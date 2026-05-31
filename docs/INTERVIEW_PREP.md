# Interview Preparation: Likely Follow-up Questions

**Q1: You used YOLOv8 for detection. Walk me through what you tried when it struggled with the partial occlusion cases in the billing clip.**
**Ideal Answer**: ByteTrack handles short-term occlusion by maintaining the Kalman filter trajectory for up to 30 frames. When a customer is partially occluded by a display, YOLO's confidence drops, but ByteTrack keeps the ID alive. I explicitly lowered the track initialization threshold to ensure partially occluded people were still tracked if their confidence hovered around 40-50%.

**Q2: Your `visitor_id` assignment uses bounding box trajectory. What breaks when a customer leaves and a different customer enters from the same direction 3 seconds later?**
**Ideal Answer**: If we only used bounding boxes, the tracker might falsely reassign the old ID to the new person. This is why I implemented OSNet Re-ID. When a new detection occurs near the `Z_ENTRY` virtual line, OSNet extracts the 512-dim embedding. If the cosine similarity to the exited visitor is low, it correctly generates a brand new `VIS_xxxx` ID.

**Q3: Your `/funnel` endpoint is accurate for the test clips. At 40 live stores sending events in real-time, what is the first thing that breaks?**
**Ideal Answer**: The Postgres database querying the entire `visitor_sessions` table with CTEs for the funnel calculation will become a massive bottleneck. The Mitigation Strategy I designed addresses this: The `Metrics Snapshot Worker` pre-calculates these aggregates every 5 minutes and caches them, shifting the burden from read-time to write-time.

**Q4: In CHOICES.md you said you considered using a VLM for zone classification but chose rule-based instead. What would make you change that decision?**
**Ideal Answer**: If store layouts changed dynamically (e.g. pop-up shops every weekend) where hardcoding polygon coordinates via `store_layout.json` became a maintenance nightmare, a VLM looking at frames to semantically segment "the makeup aisle" vs "the billing counter" would be vastly superior to rule-based geometry.
