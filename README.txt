OS PHASE 2 - MOS with paging, interrupts and error handling
============================================================
Files
  input_phase2.txt              sample jobs (with errors)
  mos_phase2.py                 Phase 2 simulator
  output_phase2.txt             output of the sample jobs
  mos_phase2_analytics.py       simulator + job analytics
  analytics_report_phase2.txt   analytics report
  timeline_phase2.csv           tick-by-tick event log
  OS_Phase2_Easy_Guide.pdf      easy guide with pictures
  MOS_Project_Report.pdf        project report + viva Q&A

Run (Python 3, no extra packages)
  python3 mos_phase2.py -i input_phase2.txt -o output_phase2.txt
  python3 mos_phase2_analytics.py            (also writes the report and timeline)
Options: --seed N (same random frames), --trace, --dump (mos_phase2.py only)
