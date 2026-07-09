# Capture seam accepts recorded video, not just live webcam

The capture module is an adapter that yields frames from **either a live webcam or a
recorded video/image sequence**, behind one interface. The team records real squat
sessions under varied conditions and **synthesises** variants (lighting, clothing,
angle) into test data.

**Why:** makes recorded sessions first-class test inputs, so the pure counting/feature
layers run headless in pytest with reproducible fixtures — no camera needed in CI. It
also directly enables the team's data plan (record → synthesise → fixture).

**Consequences:** the capture interface must expose "open from path" and "open from
device" uniformly; tests assert on recorded clips in `data/`. Live-webcam runs are just
another capture source.

See `docs/research/squat-rep-counting.md` §5.2 for public datasets to seed fixtures from.
