import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

export default function TindRefs () {
  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="ref-1">
        <AccordionTrigger>Metadata</AccordionTrigger>
        <AccordionContent>
          <p className="mb-2" style={{ whiteSpace: 'pre-line' }}>
            {props.tind_message || 'no references supplied'}
          </p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}