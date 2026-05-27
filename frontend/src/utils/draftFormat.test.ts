import { describe, expect, it } from "vitest";
import { parseDraftBody } from "./draftFormat";

describe("parseDraftBody", () => {
  it("splits inline asterisk bullets into a list", () => {
    const body =
      "For REQ-001 we propose: * Data ingestion * Data transformation * Dashboards";
    const blocks = parseDraftBody(body);
    expect(blocks[0]).toEqual({
      type: "paragraph",
      text: "For REQ-001 we propose:",
    });
    expect(blocks[1]).toEqual({
      type: "list",
      items: ["Data ingestion", "Data transformation", "Dashboards"],
    });
  });

  it("collapses extra spaces so pre-wrap gaps do not appear", () => {
    const body = "Week   1-2:   Discovery    and    workshops";
    const blocks = parseDraftBody(body);
    expect(blocks[0]).toEqual({
      type: "label",
      label: "Week 1-2",
      value: "Discovery and workshops",
    });
  });

  it("merges consecutive lines into one paragraph", () => {
    const body = "First sentence about the client.\nSecond sentence with more detail.\nThird sentence.";
    const blocks = parseDraftBody(body);
    expect(blocks).toHaveLength(1);
    expect(blocks[0]).toEqual({
      type: "paragraph",
      text: "First sentence about the client. Second sentence with more detail. Third sentence.",
    });
  });

  it("parses cover page label rows", () => {
    const body = "Proposal Title: Enterprise Solution\nClient Name: Acme Corp";
    const blocks = parseDraftBody(body);
    expect(blocks[0]).toEqual({
      type: "label",
      label: "Proposal Title",
      value: "Enterprise Solution",
    });
    expect(blocks[1]).toEqual({
      type: "label",
      label: "Client Name",
      value: "Acme Corp",
    });
  });

  it("treats numbered proposal sections as headings", () => {
    const body = "1. Executive Summary\nWe understand the client needs.";
    const blocks = parseDraftBody(body);
    expect(blocks[0]).toEqual({
      type: "heading",
      level: 2,
      text: "Executive Summary",
    });
    expect(blocks[1]).toEqual({
      type: "paragraph",
      text: "We understand the client needs.",
    });
  });
});
