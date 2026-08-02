import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ContentBlock } from "../types";
import { ContentBlocks } from "./ContentBlocks";

describe("published content block renderer", () => {
  it("renders validated prose, tables, code, and accessible local images", () => {
    const blocks: ContentBlock[] = [
      { id: "h", type: "heading", text: "Verified heading" },
      { id: "p", type: "paragraph", text: "Reviewed paragraph." },
      {
        id: "t",
        type: "comparison-table",
        columns: ["Control", "Evidence"],
        rows: [["MFA", "Authentication log"]],
      },
      { id: "c", type: "terminal", code: "safe-command --help" },
      {
        id: "i",
        type: "image",
        asset: "/assets/reviewed-diagram.png",
        alt: "Reviewed architecture diagram",
      },
    ];
    render(<ContentBlocks blocks={blocks} />);
    expect(
      screen.getByRole("heading", { name: "Verified heading" }),
    ).toBeVisible();
    expect(screen.getByRole("table")).toBeVisible();
    expect(screen.getByText("safe-command --help")).toBeVisible();
    expect(
      screen.getByRole("img", { name: "Reviewed architecture diagram" }),
    ).toHaveAttribute("src", "/assets/reviewed-diagram.png");
  });

  it("fails closed for non-local image assets", () => {
    render(
      <ContentBlocks
        blocks={[
          {
            id: "external",
            type: "image",
            asset: "https://untrusted.example/image.png",
            alt: "Untrusted",
          },
        ]}
      />,
    );
    expect(screen.queryByRole("img")).not.toBeInTheDocument();
    expect(screen.getByText(/asset is missing or unsafe/i)).toBeVisible();
  });
});
