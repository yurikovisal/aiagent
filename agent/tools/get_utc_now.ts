import { defineTool } from "eve/tools";
import { z } from "zod";

export default defineTool({
  description:
    "Return the current UTC date and time. Use when the user asks what time it is, needs a timestamp, or wants to anchor a schedule.",
  inputSchema: z.object({}),
  async execute() {
    const now = new Date();
    return {
      iso: now.toISOString(),
      unixMs: now.getTime(),
      utcDate: now.toISOString().slice(0, 10),
      utcTime: now.toISOString().slice(11, 19),
    };
  },
});
