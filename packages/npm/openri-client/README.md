# @openri/client

Lightweight ESM client for the OpenRI API.

```js
import { createOpenRIClient } from "@openri/client";

const openri = createOpenRIClient({ baseUrl: "http://127.0.0.1:8008" });
const report = await openri.runText({ text: "Methods and results...", filename: "draft.txt" });
```

OpenRI findings are evidence-backed review tasks, not misconduct determinations or automated accept/reject decisions.
