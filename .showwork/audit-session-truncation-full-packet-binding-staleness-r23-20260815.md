# Claims audit - session truncation-full-packet-binding-staleness-r23-20260815

**Verdict: GREEN**  (5/6 verified)

- OK **The truncation binding report exists** (`file_exists`, RED)
    - sources/research_20260815_showwork_truncation_full_packet_binding_staleness_r23.md exists
- .. **The report records the complete binding tuple** (`None`, RED)
    - retracted: Inline code markers separate the tuple fields; replace the aggregate regex with explicit field checks.
- OK **The report keeps future packet attachment owner-gated** (`file_contains`, RED)
    - /owner-gated/ found in sources/research_20260815_showwork_truncation_full_packet_binding_staleness_r23.md
- OK **The report records the full suite result** (`file_contains`, RED)
    - /240 passed/ found in sources/research_20260815_showwork_truncation_full_packet_binding_staleness_r23.md
- OK **The report records the run and verdict binding fields** (`file_contains`, RED)
    - /run.*verdict/ found in sources/research_20260815_showwork_truncation_full_packet_binding_staleness_r23.md
- OK **The report records packet identity and hash binding fields** (`file_contains`, RED)
    - /packet_id.*packet_hash/ found in sources/research_20260815_showwork_truncation_full_packet_binding_staleness_r23.md
