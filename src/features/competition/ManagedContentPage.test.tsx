import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Route } from "wouter";
import { ManagedContentPage } from "./ManagedContentPage";

function response(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

describe("CMS-authored learner content", () => {
  afterEach(() => { vi.unstubAllGlobals(); window.history.pushState({}, "", "/"); });
  it("runs a published CMS assessment without receiving an answer key", async () => {
    window.history.pushState({}, "", "/academy/managed/assessment/cms-assessment");
    vi.stubGlobal("fetch", vi.fn((input: RequestInfo | URL, init?: RequestInit) => init?.method === "POST" ? response({ content_version_id: "version-1", score: 1, passed: true, outcomes: [{ question_id: "question-1", correct: true, explanation: "Supported by evidence." }] }) : response({ content_id: "assessment-1", version_id: "version-1", content_type: "assessment", title: "CMS assessment", description: "Versioned assessment", version: "1.0.0", metadata: { instructions: "Choose the supported answer." }, sections: [], questions: [{ question_id: "question-1", title: "Evidence", metadata: { questionType: "single_choice", prompt: "Which value is supported?", options: ["alpha", "beta"] } }] })));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><Route path="/academy/managed/:contentType/:slug" component={ManagedContentPage} /></QueryClientProvider>);
    expect(await screen.findByRole("heading", { name: "CMS assessment" })).toBeVisible();
    expect(screen.queryByText(/answerKey/i)).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "alpha" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit assessment" }));
    await waitFor(() => expect(screen.getByRole("heading", { name: "Assessment passed" })).toBeVisible());
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/submit"), expect.objectContaining({ method: "POST" }));
  });
});
