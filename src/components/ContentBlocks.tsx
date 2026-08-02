import type { ContentBlock } from "../types";

export function ContentBlocks({ blocks }: { blocks: ContentBlock[] }) {
  return (
    <div className="content-blocks">
      {blocks.map((block) => (
        <ContentBlockView block={block} key={block.id} />
      ))}
    </div>
  );
}

function ContentBlockView({ block }: { block: ContentBlock }) {
  switch (block.type) {
    case "heading":
      return <h2>{block.text}</h2>;
    case "paragraph":
      return <p>{block.text}</p>;
    case "objective-list":
      return <ListBlock block={block} title="Objectives" />;
    case "definition":
      return <Box block={block} label="Definition" />;
    case "callout":
      return <Box block={block} label="Key point" />;
    case "warning":
      return <Box block={block} label="Safety warning" urgent />;
    case "diagram":
    case "image":
      return block.asset?.startsWith("/assets/") ? (
        <figure>
          <img src={block.asset} alt={block.alt || ""} />
          {block.text && <figcaption>{block.text}</figcaption>}
        </figure>
      ) : (
        <Box
          block={block}
          label="Diagram unavailable"
          body="The reviewed local asset is missing or unsafe."
          urgent
        />
      );
    case "comparison-table":
      return (
        <div className="content-table">
          {block.heading && <h3>{block.heading}</h3>}
          <table>
            <thead>
              <tr>
                {(block.columns || []).map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {(block.rows || []).map((row, rowIndex) => (
                <tr key={[block.id, rowIndex].join("-")}>
                  {row.map((cell, cellIndex) => (
                    <td key={[block.id, rowIndex, cellIndex].join("-")}>
                      {cell}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      );
    case "code":
    case "terminal":
    case "packet-breakdown":
    case "log-sample":
    case "forensic-artifact":
      return (
        <section className="content-code">
          <h3>{block.heading || block.type.replaceAll("-", " ")}</h3>
          <pre>
            <code>{block.code || block.text}</code>
          </pre>
        </section>
      );
    case "worked-example":
      return <Box block={block} label="Worked example" />;
    case "misconception":
      return <Box block={block} label="Common misconception" />;
    case "knowledge-check":
      return <Box block={block} label="Knowledge check" />;
    case "interactive-decision":
      return <Box block={block} label="Decision point" />;
    case "practice-launch":
      return <Box block={block} label="Approved practice" />;
    case "lab-launch":
      return <Box block={block} label="Verified lab" />;
    case "project-milestone":
      return <Box block={block} label="Project milestone" />;
    case "reference-list":
      return <ListBlock block={block} title="References" />;
    case "summary":
      return <Box block={block} label="Summary" />;
  }
}

function ListBlock({ block, title }: { block: ContentBlock; title: string }) {
  return (
    <section className="content-list">
      <h3>{block.heading || title}</h3>
      <ul>
        {(block.items || []).map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </section>
  );
}

function Box({
  block,
  label,
  body,
  urgent = false,
}: {
  block: ContentBlock;
  label: string;
  body?: string;
  urgent?: boolean;
}) {
  return (
    <aside className={urgent ? "feedback bad" : "example"}>
      <b>{block.heading || label}</b>
      <p>{body || block.body || block.text}</p>
    </aside>
  );
}
