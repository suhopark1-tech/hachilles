export interface AuditItem {
  code: string
  name: string
  passed: boolean
  score: number
  full_score: number
  detail: string
}

export interface Pillar {
  pillar: string
  score: number
  full_score: number
  passed_count: number
  items: AuditItem[]
}

export interface PatternRisk {
  pattern: string
  risk: string
  summary: string
  evidence: string[]
}

export interface ScanResult {
  hachilles_version: string
  total: number
  grade: string
  grade_label: string
  passed_rate: number
  context: Pillar
  constraint: Pillar
  entropy: Pillar
  pattern_risks: PatternRisk[]
  tech_stack: string[]
  scan_timestamp: string
  scan_errors: string[]
  dependency_cycles: unknown[][]
  layer_violations: unknown[][]
  llm_over_engineering_score: number
  go_module_name: string
  java_build_tool: string
  ts_has_eslint: boolean
  ts_has_strict: boolean
  ts_test_files: number
}

export interface HistoryRecord {
  id: number
  timestamp: string
  total_score: number
  grade: string
  passed_items: number
  total_items: number
  tech_stack: string[]
}

export interface CompareItem {
  project_path: string
  project_name: string
  total: number
  grade: string
  context_score: number
  constraint_score: number
  entropy_score: number
  tech_stack: string[]
  last_scan: string
}
