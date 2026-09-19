Step 109 changes

- Fixed unbounded surface-event queue growth in the native Android bridge.
- Surface resize/replacement callbacks now use the existing bounded/coalescing input queue (`push()`) instead of bypassing `MAX_EVENTS` with direct `deque::push_back`.
- Prevents repeated Android resize/rotation events from growing the native event queue without limit.
