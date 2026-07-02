import ReactMarkdown from 'react-markdown';

interface Props {
  markdown: string;
}

export function BenchmarkMarkdownPreview({ markdown }: Props) {
  return (
    <div className="benchmark-md overflow-y-auto max-h-96 p-3 border border-default rounded bg-panel-solid text-xs">
      <ReactMarkdown>{markdown}</ReactMarkdown>
    </div>
  );
}
