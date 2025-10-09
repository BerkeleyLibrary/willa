# pylint: skip-file

import html
import io
import logging
import os
import re
import tempfile
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path, PurePath
from typing import (
    Any,
    Iterator,
    Literal,
    Optional,
    Union,
    cast,
)
from urllib.parse import urlparse

import pypdf
import requests
from langchain_core.documents import Document
from langchain_core.document_loaders import BaseBlobParser, BaseLoader, Blob

logger = logging.getLogger(__file__)

_FORMAT_IMAGE_STR = "\n\n{image_text}\n\n"
_JOIN_IMAGES = "\n"
_JOIN_TABLES = "\n"
_DEFAULT_PAGES_DELIMITER = "\n\f"

_STD_METADATA_KEYS = {"source", "total_pages", "creationdate", "creator", "producer"}
_PDF_FILTER_WITH_LOSS = ["DCTDecode", "DCT", "JPXDecode"]
_PDF_FILTER_WITHOUT_LOSS = [
    "LZWDecode",
    "LZW",
    "FlateDecode",
    "Fl",
    "ASCII85Decode",
    "A85",
    "ASCIIHexDecode",
    "AHx",
    "RunLengthDecode",
    "RL",
    "CCITTFaxDecode",
    "CCF",
    "JBIG2Decode",
]


def _format_inner_image(blob: Blob, content: str, format: str) -> str:
    """Format the content of the image with the source of the blob.

    blob: The blob containing the image.
    format::
      The format for the parsed output.
      - "text" = return the content as is
      - "markdown-img" = wrap the content into an image Markdown link, w/ link
      pointing to (`![body)(#)`]
      - "html-img" = wrap the content as the `alt` text of a tag and link to
      (`<img alt="{body}" src="#"/>`)
    """
    if content:
        source = blob.source or "#"
        if format == "markdown-img":
            content = content.replace("]", r"\\]")
            content = f"![{content}]({source})"
        elif format == "html-img":
            content = f'<img alt="{html.escape(content, quote=True)} src="{source}" />'
    return content


def _validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Validate that the metadata has all the standard keys and the page is an integer.

    The standard keys are:
    - source
    - total_page
    - creationdate
    - creator
    - producer

    Validate that page is an integer if it is present.
    """
    if not _STD_METADATA_KEYS.issubset(metadata.keys()):
        raise ValueError("The PDF parser must valorize the standard metadata.")
    if not isinstance(metadata.get("page", 0), int):
        raise ValueError("The PDF metadata page must be a integer.")
    return metadata


def _purge_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Purge metadata from unwanted keys and normalize key names.

    Args:
        metadata: The original metadata dictionary.

    Returns:
        The cleaned and normalized the key format of metadata dictionary.
    """
    new_metadata: dict[str, Any] = {}
    map_key = {
        "page_count": "total_pages",
        "file_path": "source",
    }
    for k, v in metadata.items():
        if type(v) not in [str, int]:
            v = str(v)
        if k.startswith("/"):
            k = k[1:]
        k = k.lower()
        if k in ["creationdate", "moddate"]:
            try:
                new_metadata[k] = datetime.strptime(
                    v.replace("'", ""), "D:%Y%m%d%H%M%S%z"
                ).isoformat("T")
            except ValueError:
                new_metadata[k] = v
        elif k in map_key:
            # Normalize key with others PDF parser
            new_metadata[map_key[k]] = v
            new_metadata[k] = v
        elif isinstance(v, str):
            new_metadata[k] = v.strip()
        elif isinstance(v, int):
            new_metadata[k] = v
    return new_metadata


_PARAGRAPH_DELIMITER = [
    "\n\n\n",
    "\n\n",
]  # To insert images or table in the middle of the page.


def _merge_text_and_extras(extras: list[str], text_from_page: str) -> str:
    """Insert extras such as image/table in a text between two paragraphs if possible,
    else at the end of the text.

    Args:
        extras: List of extra content (images/tables) to insert.
        text_from_page: The text content from the page.

    Returns:
        The merged text with extras inserted.
    """

    def _recurs_merge_text_and_extras(
        extras: list[str], text_from_page: str, recurs: bool
    ) -> Optional[str]:
        if extras:
            for delim in _PARAGRAPH_DELIMITER:
                pos = text_from_page.rfind(delim)
                if pos != -1:
                    # search penultimate, to bypass an error in footer
                    previous_text = None
                    if recurs:
                        previous_text = _recurs_merge_text_and_extras(
                            extras, text_from_page[:pos], False
                        )
                    if previous_text:
                        all_text = previous_text + text_from_page[pos:]
                    else:
                        all_extras = ""
                        str_extras = "\n\n".join(filter(lambda x: x, extras))
                        if str_extras:
                            all_extras = delim + str_extras
                        all_text = (
                            text_from_page[:pos] + all_extras + text_from_page[pos:]
                        )
                    break
            else:
                all_text = None
        else:
            all_text = text_from_page
        return all_text

    all_text = _recurs_merge_text_and_extras(extras, text_from_page, True)
    if not all_text:
        all_extras = ""
        str_extras = "\n\n".join(filter(lambda x: x, extras))
        if str_extras:
            all_extras = _PARAGRAPH_DELIMITER[-1] + str_extras
        all_text = text_from_page + all_extras

    return all_text


class BaseImageBlobParser(BaseBlobParser):
    """Abstract base class for parsing image blobs into text."""

    @abstractmethod
    def _analyze_image(self, img: Any) -> str:
        """Abstract method to analyze an image and extract textual content.

        Args:
            img: The image to be analyzed.

        Returns:
          The extracted text content.
        """

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        """Lazily parse a blob and yields Documents containing the parsed content.

        Args:
            blob (Blob): The blob to be parsed.

        Yields:
            Document:
              A document containing the parsed content and metadata.
        """
        try:
            import numpy
            from PIL import Image as Img  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError(
                "`Pillow` package not found, please install it with "
                "`pip install Pillow`"
            )

        with blob.as_bytes_io() as buf:
            if blob.mimetype == "application/x-npy":
                array = numpy.load(buf)
                if array.ndim == 3 and array.shape[2] == 1:  # Grayscale image
                    img = Img.fromarray(numpy.squeeze(array, axis=2), mode="L")
                else:
                    img = Img.fromarray(array)
            else:
                img = Img.open(buf)
            content = self._analyze_image(img)
            logger.debug("Image text: %s", content.replace("\n", "\\n"))
            yield Document(
                page_content=content,
                metadata={**blob.metadata, **{"source": blob.source}},
            )


class RapidOCRBlobParser(BaseImageBlobParser):
    """Parser for extracting text from images using the RapidOCR library.

    Attributes:
        ocr:
          The RapidOCR instance for performing OCR.
    """

    def __init__(
        self,
    ) -> None:
        """
        Initializes the RapidOCRBlobParser.
        """
        super().__init__()
        self.ocr = None

    def _analyze_image(self, img: Any) -> str:
        """
        Analyzes an image and extracts text using RapidOCR.

        Args:
            img (Image):
              The image to be analyzed.

        Returns:
            str:
              The extracted text content.
        """
        if not self.ocr:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore[import-not-found]

                self.ocr = RapidOCR()
            except ImportError:
                raise ImportError(
                    "`rapidocr-onnxruntime` package not found, please install it with "
                    "`pip install rapidocr-onnxruntime`"
                )
        ocr_result, _ = self.ocr(np.array(img))  # type: ignore[misc,name-defined]
        content = ""
        if ocr_result:
            content = ("\n".join([text[1] for text in ocr_result])).strip()
        return content


class PyPDFParser(BaseBlobParser):
    """Parse a blob from a PDF using `pypdf` library.

    This class provides methods to parse a blob from a PDF document, supporting various
    configurations such as handling password-protected PDFs, extracting images.
    It integrates the 'pypdf' library for PDF processing and offers synchronous blob
    parsing.

    Examples:
        Setup:

        .. code-block:: bash

            pip install -U langchain-community pypdf

        Load a blob from a PDF file:

        .. code-block:: python

            from langchain_core.documents.base import Blob

            blob = Blob.from_path("./example_data/layout-parser-paper.pdf")

        Instantiate the parser:

        .. code-block:: python

            from langchain_community.document_loaders.parsers import PyPDFParser

            parser = PyPDFParser(
                # password = None,
                mode = "single",
                pages_delimiter = "\n\f",
                # images_parser = TesseractBlobParser(),
            )

        Lazily parse the blob:

        .. code-block:: python

            docs = []
            docs_lazy = parser.lazy_parse(blob)

            for doc in docs_lazy:
                docs.append(doc)
            print(docs[0].page_content[:100])
            print(docs[0].metadata)
    """

    def __init__(
        self,
        password: Optional[Union[str, bytes]] = None,
        extract_images: bool = False,
        *,
        mode: Literal["single", "page"] = "page",
        pages_delimiter: str = _DEFAULT_PAGES_DELIMITER,
        images_parser: Optional[BaseImageBlobParser] = None,
        images_inner_format: Literal["text", "markdown-img", "html-img"] = "text",
        extraction_mode: Literal["plain", "layout"] = "plain",
        extraction_kwargs: Optional[dict[str, Any]] = None,
    ):
        """Initialize a parser based on PyPDF.

        Args:
            password: Optional password for opening encrypted PDFs.
            extract_images: Whether to extract images from the PDF.
            mode: The extraction mode, either "single" for the entire document or "page"
                for page-wise extraction.
            pages_delimiter: A string delimiter to separate pages in single-mode
                extraction.
            images_parser: Optional image blob parser.
            images_inner_format: The format for the parsed output.
                - "text" = return the content as is
                - "markdown-img" = wrap the content into an image markdown link, w/ link
                pointing to (`![body)(#)`]
                - "html-img" = wrap the content as the `alt` text of an tag and link to
                (`<img alt="{body}" src="#"/>`)
            extraction_mode: “plain” for legacy functionality, “layout” extract text
                in a fixed width format that closely adheres to the rendered layout in
                the source pdf.
            extraction_kwargs: Optional additional parameters for the extraction
                process.

        Raises:
            ValueError: If the `mode` is not "single" or "page".
        """
        super().__init__()
        if mode not in ["single", "page"]:
            raise ValueError("mode must be single or page")
        self.extract_images = extract_images
        if extract_images and not images_parser:
            images_parser = RapidOCRBlobParser()
        self.images_parser = images_parser
        self.images_inner_format = images_inner_format
        self.password = password
        self.mode = mode
        self.pages_delimiter = pages_delimiter
        self.extraction_mode = extraction_mode
        self.extraction_kwargs = extraction_kwargs or {}

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        """
        Lazily parse the blob.
        Insert image, if possible, between two paragraphs.
        In this way, a paragraph can be continued on the next page.

        Args:
            blob: The blob to parse.

        Raises:
            ImportError: If the `pypdf` package is not found.

        Yield:
            An iterator over the parsed documents.
        """
        try:
            import pypdf
        except ImportError:
            raise ImportError(
                "`pypdf` package not found, please install it with `pip install pypdf`"
            )

        def _extract_text_from_page(page: pypdf.PageObject) -> str:
            """
            Extract text from image given the version of pypdf.

            Args:
                page: The page object to extract text from.

            Returns:
                str: The extracted text.
            """
            if pypdf.__version__.startswith("3"):
                return page.extract_text()
            else:
                return page.extract_text(
                    extraction_mode=self.extraction_mode,
                    **self.extraction_kwargs,
                )

        with blob.as_bytes_io() as pdf_file_obj:
            pdf_reader = pypdf.PdfReader(pdf_file_obj, password=self.password)

            doc_metadata = _purge_metadata(
                {"producer": "PyPDF", "creator": "PyPDF", "creationdate": ""}
                | cast(dict, pdf_reader.metadata or {})
                | {
                    "source": blob.source,
                    "total_pages": len(pdf_reader.pages),
                }
            )
            single_texts = []
            for page_number, page in enumerate(pdf_reader.pages):
                text_from_page = _extract_text_from_page(page=page)
                images_from_page = self.extract_images_from_page(page)
                all_text = _merge_text_and_extras(
                    [images_from_page], text_from_page
                ).strip()
                if self.mode == "page":
                    yield Document(
                        page_content=all_text,
                        metadata=_validate_metadata(
                            doc_metadata
                            | {
                                "page": page_number,
                                "page_label": pdf_reader.page_labels[page_number],
                            }
                        ),
                    )
                else:
                    single_texts.append(all_text)
            if self.mode == "single":
                yield Document(
                    page_content=self.pages_delimiter.join(single_texts),
                    metadata=_validate_metadata(doc_metadata),
                )

    def extract_images_from_page(self, page: pypdf._page.PageObject) -> str:
        """Extract images from a PDF page and get the text using images_to_text.

        Args:
            page: The page object from which to extract images.

        Returns:
            str: The extracted text from the images on the page.
        """
        if not self.images_parser:
            return ""
        import numpy as np
        import pypdf
        from PIL import Image

        if "/XObject" not in cast(dict, page["/Resources"]).keys():
            return ""

        xObject = cast(dict, page["/Resources"])["/XObject"].get_object()
        images = []
        for obj in xObject:
            np_image: Any = None
            if xObject[obj]["/Subtype"] == "/Image":
                img_filter = (
                    xObject[obj]["/Filter"][1:]
                    if type(xObject[obj]["/Filter"]) is pypdf.generic._base.NameObject
                    else xObject[obj]["/Filter"][0][1:]
                )
                if img_filter in _PDF_FILTER_WITHOUT_LOSS:
                    height, width = xObject[obj]["/Height"], xObject[obj]["/Width"]

                    np_image = np.frombuffer(
                        xObject[obj].get_data(), dtype=np.uint8
                    ).reshape(height, width, -1)
                elif img_filter in _PDF_FILTER_WITH_LOSS:
                    np_image = np.array(Image.open(io.BytesIO(xObject[obj].get_data())))

                else:
                    logger.warning("Unknown PDF Filter!")
                if np_image is not None:
                    image_bytes = io.BytesIO()

                    if image_bytes.getbuffer().nbytes == 0:
                        continue

                    Image.fromarray(np_image).save(image_bytes, format="PNG")
                    blob = Blob.from_data(image_bytes.getvalue(), mime_type="image/png")
                    image_text = next(self.images_parser.lazy_parse(blob)).page_content
                    images.append(
                        _format_inner_image(blob, image_text, self.images_inner_format)
                    )
        return _FORMAT_IMAGE_STR.format(
            image_text=_JOIN_IMAGES.join(filter(None, images))
        )


class BasePDFLoader(BaseLoader, ABC):
    """Base Loader class for `PDF` files.

    If the file is a web path, it will download it to a temporary file, use it, then
        clean up the temporary file after completion.
    """

    def __init__(
        self, file_path: Union[str, PurePath], *, headers: Optional[dict] = None
    ):
        """Initialize with a file path.

        Args:
            file_path: Either a local, S3 or web path to a PDF file.
            headers: Headers to use for GET request to download a file from a web path.
        """
        self.file_path = str(file_path)
        self.web_path = None
        self.headers = headers
        if "~" in self.file_path:
            self.file_path = os.path.expanduser(self.file_path)

        # If the file is a web path or S3, download it to a temporary file,
        # and use that. It's better to use a BlobLoader.
        if not os.path.isfile(self.file_path) and self._is_valid_url(self.file_path):
            self.temp_dir = tempfile.TemporaryDirectory()
            _, suffix = os.path.splitext(self.file_path)
            if self._is_s3_presigned_url(self.file_path):
                suffix = urlparse(self.file_path).path.split("/")[-1]
            temp_pdf = os.path.join(self.temp_dir.name, f"tmp{suffix}")
            self.web_path = self.file_path
            if not self._is_s3_url(self.file_path):
                r = requests.get(self.file_path, headers=self.headers)
                if r.status_code != 200:
                    raise ValueError(
                        "Check the url of your file; returned status code %s"
                        % r.status_code
                    )

                with open(temp_pdf, mode="wb") as f:
                    f.write(r.content)
                self.file_path = str(temp_pdf)
        elif not os.path.isfile(self.file_path):
            raise ValueError("File path %s is not a valid file or url" % self.file_path)

    def __del__(self) -> None:
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if the url is valid."""
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    @staticmethod
    def _is_s3_url(url: str) -> bool:
        """check if the url is S3"""
        try:
            result = urlparse(url)
            if result.scheme == "s3" and result.netloc:
                return True
            return False
        except ValueError:
            return False

    @staticmethod
    def _is_s3_presigned_url(url: str) -> bool:
        """Check if the url is a presigned S3 url."""
        try:
            result = urlparse(url)
            return bool(re.search(r"\.s3\.amazonaws\.com$", result.netloc))
        except ValueError:
            return False

    @property
    def source(self) -> str:
        return self.web_path if self.web_path is not None else self.file_path


class PyPDFLoader(BasePDFLoader):
    """Load and parse a PDF file using 'pypdf' library.

    This class provides methods to load and parse PDF documents, supporting various
    configurations such as handling password-protected files, extracting images, and
    defining extraction mode. It integrates the `pypdf` library for PDF processing and
    offers both synchronous and asynchronous document loading.

    Examples:
        Setup:

        .. code-block:: bash

            pip install -U langchain-community pypdf

        Instantiate the loader:

        .. code-block:: python

            from langchain_community.document_loaders import PyPDFLoader

            loader = PyPDFLoader(
                file_path = "./example_data/layout-parser-paper.pdf",
                # headers = None
                # password = None,
                mode = "single",
                pages_delimiter = "\n\f",
                # extract_images = True,
                # images_parser = RapidOCRBlobParser(),
            )

        Lazy load documents:

        .. code-block:: python

            docs = []
            docs_lazy = loader.lazy_load()

            for doc in docs_lazy:
                docs.append(doc)
            print(docs[0].page_content[:100])
            print(docs[0].metadata)

        Load documents asynchronously:

        .. code-block:: python

            docs = await loader.aload()
            print(docs[0].page_content[:100])
            print(docs[0].metadata)
    """

    def __init__(
        self,
        file_path: Union[str, PurePath],
        password: Optional[Union[str, bytes]] = None,
        headers: Optional[dict] = None,
        extract_images: bool = False,
        *,
        mode: Literal["single", "page"] = "page",
        images_parser: Optional[BaseImageBlobParser] = None,
        images_inner_format: Literal["text", "markdown-img", "html-img"] = "text",
        pages_delimiter: str = _DEFAULT_PAGES_DELIMITER,
        extraction_mode: Literal["plain", "layout"] = "plain",
        extraction_kwargs: Optional[dict] = None,
    ) -> None:
        """Initialize with a file path.

        Args:
            file_path: The path to the PDF file to be loaded.
            headers: Optional headers to use for GET request to download a file from a
              web path.
            password: Optional password for opening encrypted PDFs.
            mode: The extraction mode, either "single" for the entire document or "page"
                for page-wise extraction.
            pages_delimiter: A string delimiter to separate pages in single-mode
                extraction.
            extract_images: Whether to extract images from the PDF.
            images_parser: Optional image blob parser.
            images_inner_format: The format for the parsed output.
                - "text" = return the content as is
                - "markdown-img" = wrap the content into an image markdown link, w/ link
                pointing to (`![body)(#)`]
                - "html-img" = wrap the content as the `alt` text of an tag and link to
                (`<img alt="{body}" src="#"/>`)
            extraction_mode: “plain” for legacy functionality, “layout” extract text
                in a fixed width format that closely adheres to the rendered layout in
                the source pdf
            extraction_kwargs: Optional additional parameters for the extraction
                process.

        Returns:
            This method does not directly return data. Use the `load`, `lazy_load` or
            `aload` methods to retrieve parsed documents with content and metadata.
        """
        super().__init__(file_path, headers=headers)
        self.parser = PyPDFParser(
            password=password,
            mode=mode,
            extract_images=extract_images,
            images_parser=images_parser,
            images_inner_format=images_inner_format,
            pages_delimiter=pages_delimiter,
            extraction_mode=extraction_mode,
            extraction_kwargs=extraction_kwargs,
        )

    def lazy_load(
        self,
    ) -> Iterator[Document]:
        """
        Lazy load given path as pages.
        Insert image, if possible, between two paragraphs.
        In this way, a paragraph can be continued on the next page.
        """
        if self.web_path:
            blob = Blob.from_data(open(self.file_path, "rb").read(), path=self.web_path)
        else:
            blob = Blob.from_path(self.file_path)
        yield from self.parser.lazy_parse(blob)


class PyPDFDirectoryLoader(BaseLoader):
    """Load and parse a directory of PDF files using 'pypdf' library.

    This class provides methods to load and parse multiple PDF documents in a directory,
    supporting options for recursive search, handling password-protected files,
    extracting images, and defining extraction modes. It integrates the `pypdf` library
    for PDF processing and offers synchronous document loading.

    Examples:
        Setup:

        .. code-block:: bash

            pip install -U langchain-community pypdf

        Instantiate the loader:

        .. code-block:: python

            from langchain_community.document_loaders import PyPDFDirectoryLoader

            loader = PyPDFDirectoryLoader(
                path = "./example_data/",
                glob = "**/[!.]*.pdf",
                silent_errors = False,
                load_hidden = False,
                recursive = False,
                extract_images = False,
                password = None,
                mode = "page",
                images_to_text = None,
                headers = None,
                extraction_mode = "plain",
                # extraction_kwargs = None,
            )

        Load documents:

        .. code-block:: python

            docs = loader.load()
            print(docs[0].page_content[:100])
            print(docs[0].metadata)

        Load documents asynchronously:

        .. code-block:: python

            docs = await loader.aload()
            print(docs[0].page_content[:100])
            print(docs[0].metadata)
    """

    def __init__(
        self,
        path: Union[str, PurePath],
        glob: str = "**/[!.]*.pdf",
        silent_errors: bool = False,
        load_hidden: bool = False,
        recursive: bool = False,
        extract_images: bool = False,
        *,
        password: Optional[str] = None,
        mode: Literal["single", "page"] = "page",
        images_parser: Optional[BaseImageBlobParser] = None,
        headers: Optional[dict] = None,
        extraction_mode: Literal["plain", "layout"] = "plain",
        extraction_kwargs: Optional[dict] = None,
    ):
        """Initialize with a directory path.

        Args:
            path: The path to the directory containing PDF files to be loaded.
            glob: The glob pattern to match files in the directory.
            silent_errors: Whether to log errors instead of raising them.
            load_hidden: Whether to include hidden files in the search.
            recursive: Whether to search subdirectories recursively.
            extract_images: Whether to extract images from PDFs.
            password: Optional password for opening encrypted PDFs.
            mode: The extraction mode, either "single" for extracting the entire
                document or "page" for page-wise extraction.
            images_parser: Optional image blob parser..
            headers: Optional headers to use for GET request to download a file from a
              web path.
            extraction_mode: “plain” for legacy functionality, “layout” for
              experimental layout mode functionality
            extraction_kwargs: Optional additional parameters for the extraction
              process.

        Returns:
            This method does not directly return data. Use the `load` method to
            retrieve parsed documents with content and metadata.
        """
        self.password = password
        self.mode = mode
        self.path = path
        self.glob = glob
        self.load_hidden = load_hidden
        self.recursive = recursive
        self.silent_errors = silent_errors
        self.extract_images = extract_images
        self.images_parser = images_parser
        self.headers = headers
        self.extraction_mode = extraction_mode
        self.extraction_kwargs = extraction_kwargs

    @staticmethod
    def _is_visible(path: PurePath) -> bool:
        return not any(part.startswith(".") for part in path.parts)

    def load(self) -> list[Document]:
        p = Path(self.path)
        docs = []
        items = p.rglob(self.glob) if self.recursive else p.glob(self.glob)
        for i in items:
            if i.is_file():
                if self._is_visible(i.relative_to(p)) or self.load_hidden:
                    try:
                        loader = PyPDFLoader(
                            str(i),
                            password=self.password,
                            mode=self.mode,
                            extract_images=self.extract_images,
                            images_parser=self.images_parser,
                            headers=self.headers,
                            extraction_mode=self.extraction_mode,
                            extraction_kwargs=self.extraction_kwargs,
                        )
                        sub_docs = loader.load()
                        for doc in sub_docs:
                            doc.metadata["source"] = str(i)
                        docs.extend(sub_docs)
                    except Exception as e:
                        if self.silent_errors:
                            logger.warning(e)
                        else:
                            raise e
        return docs
