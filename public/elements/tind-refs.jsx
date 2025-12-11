import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion"

export default function TindRefs () {
  const parseTindReference = (msg) => {
    const ref = {
      title: null,
      interviewers: [],
      interviewees: [],
      project: null,
      link: null,
    };
    const lines = msg.split('\n').filter(line => line.trim() !== '');

    lines.forEach(line => {
      const parts = line.split(':');
      const key = parts[0].trim();
      const value = parts.slice(1).join(':').trim();

      switch (key) {
        case 'Title':
          ref.title = value;
          break;
        case 'Contributor':
          // if value ends in interviewee or interviewer, assign accordingly
          if (value.endsWith(' interviewer')) {
            ref.interviewers.push(value.replace(' interviewer', '').trim());
          } else if (value.endsWith(' interviewee')) {
            ref.interviewees.push(value.replace(' interviewee', '').trim());
          }
          break;
        case 'Project Name':
          ref.project = value;
          break;
        case 'Catalogue Link':
          ref.link = value;
          break;
      }
    });
    return ref;
  };
  
  let count = 0;


  const buildTindMessage = () => {
    const originalMessage = props.tind_message || 'no references supplied';
    if (originalMessage === 'no references supplied') {
      return originalMessage;
    }
    // Split message into parts by '___________' separator
    const parts = originalMessage.split('___________');
    
    const references = parts
      .filter(part => part.trim() !== '')
      .map(part => parseTindReference(part));

    count = references.length;
    return (
      <div>
        {references.map((ref, index) => (
          <div key={index}>
            <a href={ref.link} style={{ textDecoration: 'underline' }}>{ref.title}</a>
            <p>
              Interviewee(s): {ref.interviewees.join(' | ')}<br />
              Interviewer(s): {ref.interviewers.join(' | ')}<br />
              Project Name: {ref.project}<br />
            </p>
            ___________
          </div>
        ))}
      </div>
    );
  };
  const tindMessage = buildTindMessage();

  return (
    <Accordion type="single" collapsible className="w-full">
      <AccordionItem value="ref-1">
        <AccordionTrigger>References{count > 0 ? ` (${count})` : ''}</AccordionTrigger>
        <AccordionContent>
          <p className="mb-2" style={{ whiteSpace: 'pre-line' }}>
            {tindMessage}
          </p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  )
}