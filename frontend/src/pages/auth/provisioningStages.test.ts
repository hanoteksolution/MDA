import { describe, expect, it } from "vitest";
import { summarizeProvisioningStages } from "./provisioningStages";

describe("summarizeProvisioningStages", () => {
  it("keeps server order and the latest status per stage", () => {
    const rows = summarizeProvisioningStages([
      { stage: "company", status: "running" },
      { stage: "company", status: "succeeded" },
      { stage: "workspace", status: "succeeded" },
      { stage: "accounting", status: "running" },
    ]);
    expect(rows).toEqual([
      { id: "company", status: "succeeded", label: "Creating company" },
      { id: "workspace", status: "succeeded", label: "Reserving workspace URL" },
      { id: "accounting", status: "running", label: "Preparing accounting" },
    ]);
  });

  it("returns nothing when the server reported no stages", () => {
    expect(summarizeProvisioningStages(undefined)).toEqual([]);
    expect(summarizeProvisioningStages([])).toEqual([]);
  });

  it("labels unknown stages from their id instead of dropping them", () => {
    expect(summarizeProvisioningStages([{ stage: "dns_check", status: "succeeded" }])).toEqual([
      { id: "dns_check", status: "succeeded", label: "Dns check" },
    ]);
  });
});
