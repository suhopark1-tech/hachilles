import { useState } from "react"
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts"
import {
  scanProject,
  getHistory,
  compareProjects,
  generateAgentsMd,
} from "./api"
import type {
  ScanResult,
  HistoryRecord,
  CompareItem,
  AuditItem,
  Pillar,
} from "./types"
import "./index.css"

function ScoreGauge({ score, max }: { score: number; max: number }) {
  const percentage = (score / max) * 100
  const color =
    percentage >= 80
      ? "var(--green)"
      : percentage >= 60
        ? "var(--yellow)"
        : "var(--red)"

  return (
    <div
      style={{
        width: "200px",
        height: "200px",
        borderRadius: "50%",
        background: "conic-gradient(var(--accent) 0deg, var(--card) 0deg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        backgroundImage: `conic-gradient(${color} ${percentage * 3.6}deg, var(--card) ${percentage * 3.6}deg)`,
      }}
    >
      <div
        style={{
          textAlign: "center",
          fontSize: "32px",
          fontWeight: "bold",
          color,
        }}
      >
        {score}
      </div>
    </div>
  )
}

function PillarBar({ pillar }: { pillar: Pillar }) {
  const percentage = (pillar.score / pillar.full_score) * 100

  return (
    <div
      style={{
        marginBottom: "20px",
        padding: "15px",
        background: "var(--card)",
        borderRadius: "8px",
        border: "1px solid var(--border)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          marginBottom: "8px",
        }}
      >
        <span style={{ fontWeight: "bold", textTransform: "uppercase" }}>
          {pillar.pillar}
        </span>
        <span style={{ color: "var(--dim)" }}>
          {pillar.score}/{pillar.full_score}
        </span>
      </div>
      <div
        style={{
          width: "100%",
          height: "8px",
          background: "var(--border)",
          borderRadius: "4px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${percentage}%`,
            background:
              percentage >= 80
                ? "var(--green)"
                : percentage >= 60
                  ? "var(--yellow)"
                  : "var(--red)",
            transition: "width 0.3s ease",
          }}
        />
      </div>
      <div style={{ marginTop: "8px", color: "var(--dim)", fontSize: "12px" }}>
        {pillar.passed_count}/{pillar.items.length} 항목 통과
      </div>
    </div>
  )
}

function AuditTable({ items }: { items: AuditItem[] }) {
  return (
    <table
      style={{
        width: "100%",
        borderCollapse: "collapse",
        marginTop: "10px",
      }}
    >
      <thead>
        <tr
          style={{
            borderBottom: "1px solid var(--border)",
            background: "var(--card)",
          }}
        >
          <th style={{ padding: "10px", textAlign: "left" }}>코드</th>
          <th style={{ padding: "10px", textAlign: "left" }}>항목</th>
          <th style={{ padding: "10px", textAlign: "center" }}>상태</th>
          <th style={{ padding: "10px", textAlign: "right" }}>점수</th>
          <th style={{ padding: "10px", textAlign: "left" }}>설명</th>
        </tr>
      </thead>
      <tbody>
        {items.map((item) => (
          <tr
            key={item.code}
            style={{ borderBottom: "1px solid var(--border)" }}
          >
            <td
              style={{
                padding: "10px",
                fontFamily: "monospace",
                color: "var(--accent)",
              }}
            >
              {item.code}
            </td>
            <td style={{ padding: "10px" }}>{item.name}</td>
            <td style={{ padding: "10px", textAlign: "center" }}>
              <span
                style={{
                  padding: "4px 8px",
                  borderRadius: "4px",
                  background: item.passed ? "var(--green)" : "var(--red)",
                  color: "white",
                  fontSize: "12px",
                  fontWeight: "bold",
                }}
              >
                {item.passed ? "PASS" : "FAIL"}
              </span>
            </td>
            <td style={{ padding: "10px", textAlign: "right" }}>
              {item.score}/{item.full_score}
            </td>
            <td style={{ padding: "10px", color: "var(--dim)" }}>
              {item.detail}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function PatternRiskTable({
  risks,
}: {
  risks: Array<{
    pattern: string
    risk: string
    summary: string
    evidence: string[]
  }>
}) {
  return (
    <table
      style={{
        width: "100%",
        borderCollapse: "collapse",
        marginTop: "10px",
      }}
    >
      <thead>
        <tr
          style={{
            borderBottom: "1px solid var(--border)",
            background: "var(--card)",
          }}
        >
          <th style={{ padding: "10px", textAlign: "left" }}>패턴</th>
          <th style={{ padding: "10px", textAlign: "center" }}>위험도</th>
          <th style={{ padding: "10px", textAlign: "left" }}>설명</th>
          <th style={{ padding: "10px", textAlign: "left" }}>근거</th>
        </tr>
      </thead>
      <tbody>
        {risks.map((risk) => (
          <tr
            key={risk.pattern}
            style={{ borderBottom: "1px solid var(--border)" }}
          >
            <td style={{ padding: "10px", fontWeight: "bold" }}>
              {risk.pattern}
            </td>
            <td style={{ padding: "10px", textAlign: "center" }}>
              <span
                style={{
                  padding: "4px 8px",
                  borderRadius: "4px",
                  background:
                    risk.risk === "critical"
                      ? "var(--red)"
                      : risk.risk === "high"
                        ? "var(--yellow)"
                        : "var(--accent)",
                  color: "white",
                  fontSize: "12px",
                  fontWeight: "bold",
                }}
              >
                {risk.risk.toUpperCase()}
              </span>
            </td>
            <td style={{ padding: "10px", color: "var(--dim)" }}>
              {risk.summary}
            </td>
            <td style={{ padding: "10px", color: "var(--dim)", fontSize: "12px" }}>
              {risk.evidence.slice(0, 2).join(", ")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function HistoryChart({ records }: { records: HistoryRecord[] }) {
  const data = records
    .reverse()
    .map((r) => ({
      date: r.timestamp.slice(0, 10),
      total: r.total_score,
      passed: r.passed_items,
    }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data}>
        <CartesianGrid stroke="var(--border)" />
        <XAxis stroke="var(--dim)" />
        <YAxis stroke="var(--dim)" />
        <Tooltip
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            color: "var(--text)",
          }}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="total"
          stroke="var(--accent)"
          name="전체 점수"
        />
        <Line
          type="monotone"
          dataKey="passed"
          stroke="var(--green)"
          name="통과 항목"
        />
      </LineChart>
    </ResponsiveContainer>
  )
}

function CompareChart({ items }: { items: CompareItem[] }) {
  const data = items.map((item) => ({
    name: item.project_name,
    context: item.context_score,
    constraint: item.constraint_score,
    entropy: item.entropy_score,
  }))

  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data}>
        <CartesianGrid stroke="var(--border)" />
        <XAxis stroke="var(--dim)" />
        <YAxis stroke="var(--dim)" />
        <Tooltip
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            color: "var(--text)",
          }}
        />
        <Legend />
        <Bar dataKey="context" fill="var(--accent)" name="Context" />
        <Bar dataKey="constraint" fill="var(--green)" name="Constraint" />
        <Bar dataKey="entropy" fill="var(--yellow)" name="Entropy" />
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function App() {
  const [tab, setTab] = useState<"scan" | "history" | "compare" | "agents">(
    "scan"
  )
  const [scanPath, setScanPath] = useState("")
  const [scanResult, setScanResult] = useState<ScanResult | null>(null)
  const [scanLoading, setScanLoading] = useState(false)
  const [scanError, setScanError] = useState("")

  const [historyPath, setHistoryPath] = useState("")
  const [historyRecords, setHistoryRecords] = useState<HistoryRecord[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState("")

  const [comparePaths, setComparePaths] = useState("")
  const [compareItems, setCompareItems] = useState<CompareItem[]>([])
  const [compareLoading, setCompareLoading] = useState(false)
  const [compareError, setCompareError] = useState("")

  const [agentsPath, setAgentsPath] = useState("")
  const [agentsContent, setAgentsContent] = useState("")
  const [agentsLoading, setAgentsLoading] = useState(false)
  const [agentsError, setAgentsError] = useState("")

  const [scanWithLlm, setScanWithLlm] = useState(false)
  const [scanWithHistory, setScanWithHistory] = useState(false)

  const handleScan = async () => {
    if (!scanPath) {
      setScanError("경로를 입력하세요")
      return
    }
    setScanLoading(true)
    setScanError("")
    try {
      const result = await scanProject(scanPath, scanWithLlm, scanWithHistory)
      setScanResult(result)
    } catch (err) {
      setScanError(err instanceof Error ? err.message : "스캔 실패")
    } finally {
      setScanLoading(false)
    }
  }

  const handleHistory = async () => {
    if (!historyPath) {
      setHistoryError("경로를 입력하세요")
      return
    }
    setHistoryLoading(true)
    setHistoryError("")
    try {
      const data = await getHistory(historyPath)
      setHistoryRecords(data.records)
    } catch (err) {
      setHistoryError(err instanceof Error ? err.message : "이력 조회 실패")
    } finally {
      setHistoryLoading(false)
    }
  }

  const handleCompare = async () => {
    const paths = comparePaths
      .split("\n")
      .map((p) => p.trim())
      .filter((p) => p)
    if (paths.length < 2) {
      setCompareError("2개 이상의 경로를 입력하세요 (한 줄에 하나)")
      return
    }
    setCompareLoading(true)
    setCompareError("")
    try {
      const data = await compareProjects(paths)
      setCompareItems(data.projects)
    } catch (err) {
      setCompareError(
        err instanceof Error ? err.message : "비교 조회 실패"
      )
    } finally {
      setCompareLoading(false)
    }
  }

  const handleAgents = async () => {
    if (!agentsPath) {
      setAgentsError("경로를 입력하세요")
      return
    }
    setAgentsLoading(true)
    setAgentsError("")
    try {
      const data = await generateAgentsMd(agentsPath)
      setAgentsContent(data.content)
    } catch (err) {
      setAgentsError(err instanceof Error ? err.message : "생성 실패")
    } finally {
      setAgentsLoading(false)
    }
  }

  const downloadAgents = () => {
    const blob = new Blob([agentsContent], { type: "text/markdown" })
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url
    a.download = "AGENTS.md"
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--bg)",
        color: "var(--text)",
        padding: "20px",
      }}
    >
      <div
        style={{
          maxWidth: "1400px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            marginBottom: "30px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <h1>HAchilles Dashboard</h1>
          <span style={{ color: "var(--dim)", fontSize: "14px" }}>
            Phase 3 REST API
          </span>
        </div>

        <div
          style={{
            display: "flex",
            gap: "10px",
            marginBottom: "30px",
            borderBottom: "1px solid var(--border)",
          }}
        >
          {(
            [
              { key: "scan", label: "진단" },
              { key: "history", label: "이력" },
              { key: "compare", label: "팀 비교" },
              { key: "agents", label: "AGENTS.md" },
            ] as const
          ).map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              style={{
                padding: "12px 20px",
                background: tab === t.key ? "var(--accent)" : "transparent",
                color: "var(--text)",
                border: "none",
                cursor: "pointer",
                borderBottom:
                  tab === t.key ? "2px solid var(--accent)" : "2px solid transparent",
                fontSize: "14px",
                fontWeight: "bold",
              }}
            >
              {t.label}
            </button>
          ))}
        </div>

        {tab === "scan" && (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <h2>프로젝트 하네스 진단</h2>
            <div style={{ marginTop: "20px", display: "flex", gap: "10px" }}>
              <input
                type="text"
                value={scanPath}
                onChange={(e) => setScanPath(e.target.value)}
                placeholder="프로젝트 경로 (절대 또는 상대)"
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  color: "var(--text)",
                }}
              />
              <button
                onClick={handleScan}
                disabled={scanLoading}
                style={{
                  padding: "10px 20px",
                  background: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                {scanLoading ? "스캔 중..." : "스캔"}
              </button>
            </div>
            <div style={{ marginTop: "15px", display: "flex", gap: "20px" }}>
              <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="checkbox"
                  checked={scanWithLlm}
                  onChange={(e) => setScanWithLlm(e.target.checked)}
                />
                LLM 분석 활성화
              </label>
              <label style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <input
                  type="checkbox"
                  checked={scanWithHistory}
                  onChange={(e) => setScanWithHistory(e.target.checked)}
                />
                이력 저장
              </label>
            </div>

            {scanError && (
              <div
                style={{
                  marginTop: "15px",
                  padding: "10px",
                  background: "var(--red)",
                  borderRadius: "4px",
                  color: "white",
                }}
              >
                {scanError}
              </div>
            )}

            {scanResult && (
              <div style={{ marginTop: "30px" }}>
                <div
                  style={{
                    display: "grid",
                    gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))",
                    gap: "20px",
                    marginBottom: "30px",
                  }}
                >
                  <div style={{ textAlign: "center" }}>
                    <ScoreGauge score={scanResult.total} max={100} />
                    <div
                      style={{
                        marginTop: "10px",
                        fontSize: "14px",
                        color: "var(--dim)",
                      }}
                    >
                      {scanResult.grade} ({scanResult.grade_label})
                    </div>
                  </div>
                  <div>
                    <PillarBar pillar={scanResult.context} />
                  </div>
                  <div>
                    <PillarBar pillar={scanResult.constraint} />
                  </div>
                  <div>
                    <PillarBar pillar={scanResult.entropy} />
                  </div>
                </div>

                <div style={{ marginTop: "30px" }}>
                  <h3>기술 스택</h3>
                  <div style={{ display: "flex", gap: "10px", flexWrap: "wrap", marginTop: "10px" }}>
                    {scanResult.tech_stack.map((tech) => (
                      <span
                        key={tech}
                        style={{
                          padding: "6px 12px",
                          background: "var(--accent)",
                          borderRadius: "4px",
                          fontSize: "12px",
                        }}
                      >
                        {tech}
                      </span>
                    ))}
                  </div>
                </div>

                {scanResult.pattern_risks.length > 0 && (
                  <div style={{ marginTop: "30px" }}>
                    <h3>패턴 위험도</h3>
                    <PatternRiskTable risks={scanResult.pattern_risks} />
                  </div>
                )}

                <div style={{ marginTop: "30px" }}>
                  <h3>Context Engineering</h3>
                  <AuditTable items={scanResult.context.items} />
                </div>

                <div style={{ marginTop: "30px" }}>
                  <h3>Architecture Constraint</h3>
                  <AuditTable items={scanResult.constraint.items} />
                </div>

                <div style={{ marginTop: "30px" }}>
                  <h3>Entropy Management</h3>
                  <AuditTable items={scanResult.entropy.items} />
                </div>

                {scanResult.scan_errors.length > 0 && (
                  <div style={{ marginTop: "30px" }}>
                    <h3>스캔 중 발생한 오류</h3>
                    <ul style={{ color: "var(--dim)" }}>
                      {scanResult.scan_errors.map((err, i) => (
                        <li key={i}>{err}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {tab === "history" && (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <h2>진단 이력</h2>
            <div style={{ marginTop: "20px", display: "flex", gap: "10px" }}>
              <input
                type="text"
                value={historyPath}
                onChange={(e) => setHistoryPath(e.target.value)}
                placeholder="프로젝트 경로"
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  color: "var(--text)",
                }}
              />
              <button
                onClick={handleHistory}
                disabled={historyLoading}
                style={{
                  padding: "10px 20px",
                  background: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                {historyLoading ? "로딩 중..." : "조회"}
              </button>
            </div>

            {historyError && (
              <div
                style={{
                  marginTop: "15px",
                  padding: "10px",
                  background: "var(--red)",
                  borderRadius: "4px",
                  color: "white",
                }}
              >
                {historyError}
              </div>
            )}

            {historyRecords.length > 0 && (
              <div style={{ marginTop: "30px" }}>
                <h3>점수 추이</h3>
                <HistoryChart records={historyRecords} />

                <h3 style={{ marginTop: "30px" }}>이력 기록</h3>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    marginTop: "10px",
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid var(--border)",
                        background: "var(--bg)",
                      }}
                    >
                      <th style={{ padding: "10px", textAlign: "left" }}>날짜</th>
                      <th style={{ padding: "10px", textAlign: "right" }}>점수</th>
                      <th style={{ padding: "10px", textAlign: "center" }}>등급</th>
                      <th style={{ padding: "10px", textAlign: "center" }}>
                        통과율
                      </th>
                      <th style={{ padding: "10px", textAlign: "left" }}>
                        기술 스택
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {historyRecords.map((record) => (
                      <tr
                        key={record.id}
                        style={{ borderBottom: "1px solid var(--border)" }}
                      >
                        <td style={{ padding: "10px" }}>
                          {record.timestamp.slice(0, 10)}
                        </td>
                        <td style={{ padding: "10px", textAlign: "right" }}>
                          {record.total_score}
                        </td>
                        <td style={{ padding: "10px", textAlign: "center" }}>
                          {record.grade}
                        </td>
                        <td style={{ padding: "10px", textAlign: "center" }}>
                          {record.passed_items}/{record.total_items}
                        </td>
                        <td style={{ padding: "10px", color: "var(--dim)" }}>
                          {record.tech_stack.join(", ")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === "compare" && (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <h2>팀 프로젝트 비교</h2>
            <div style={{ marginTop: "20px" }}>
              <textarea
                value={comparePaths}
                onChange={(e) => setComparePaths(e.target.value)}
                placeholder="프로젝트 경로들 (한 줄에 하나)"
                style={{
                  width: "100%",
                  padding: "10px",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  color: "var(--text)",
                  minHeight: "100px",
                  fontFamily: "monospace",
                }}
              />
              <button
                onClick={handleCompare}
                disabled={compareLoading}
                style={{
                  marginTop: "10px",
                  padding: "10px 20px",
                  background: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                {compareLoading ? "비교 중..." : "비교"}
              </button>
            </div>

            {compareError && (
              <div
                style={{
                  marginTop: "15px",
                  padding: "10px",
                  background: "var(--red)",
                  borderRadius: "4px",
                  color: "white",
                }}
              >
                {compareError}
              </div>
            )}

            {compareItems.length > 0 && (
              <div style={{ marginTop: "30px" }}>
                <h3>점수 비교</h3>
                <CompareChart items={compareItems} />

                <h3 style={{ marginTop: "30px" }}>상세 비교</h3>
                <table
                  style={{
                    width: "100%",
                    borderCollapse: "collapse",
                    marginTop: "10px",
                  }}
                >
                  <thead>
                    <tr
                      style={{
                        borderBottom: "1px solid var(--border)",
                        background: "var(--bg)",
                      }}
                    >
                      <th style={{ padding: "10px", textAlign: "left" }}>프로젝트</th>
                      <th style={{ padding: "10px", textAlign: "right" }}>전체</th>
                      <th style={{ padding: "10px", textAlign: "right" }}>Context</th>
                      <th style={{ padding: "10px", textAlign: "right" }}>
                        Constraint
                      </th>
                      <th style={{ padding: "10px", textAlign: "right" }}>Entropy</th>
                      <th style={{ padding: "10px", textAlign: "center" }}>등급</th>
                    </tr>
                  </thead>
                  <tbody>
                    {compareItems.map((item) => (
                      <tr
                        key={item.project_path}
                        style={{ borderBottom: "1px solid var(--border)" }}
                      >
                        <td style={{ padding: "10px", fontWeight: "bold" }}>
                          {item.project_name}
                        </td>
                        <td style={{ padding: "10px", textAlign: "right" }}>
                          {item.total}
                        </td>
                        <td style={{ padding: "10px", textAlign: "right" }}>
                          {item.context_score}
                        </td>
                        <td style={{ padding: "10px", textAlign: "right" }}>
                          {item.constraint_score}
                        </td>
                        <td style={{ padding: "10px", textAlign: "right" }}>
                          {item.entropy_score}
                        </td>
                        <td style={{ padding: "10px", textAlign: "center" }}>
                          {item.grade}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {tab === "agents" && (
          <div
            style={{
              background: "var(--card)",
              border: "1px solid var(--border)",
              borderRadius: "8px",
              padding: "20px",
            }}
          >
            <h2>AGENTS.md 생성</h2>
            <div style={{ marginTop: "20px", display: "flex", gap: "10px" }}>
              <input
                type="text"
                value={agentsPath}
                onChange={(e) => setAgentsPath(e.target.value)}
                placeholder="프로젝트 경로"
                style={{
                  flex: 1,
                  padding: "10px",
                  background: "var(--bg)",
                  border: "1px solid var(--border)",
                  borderRadius: "4px",
                  color: "var(--text)",
                }}
              />
              <button
                onClick={handleAgents}
                disabled={agentsLoading}
                style={{
                  padding: "10px 20px",
                  background: "var(--accent)",
                  color: "white",
                  border: "none",
                  borderRadius: "4px",
                  cursor: "pointer",
                }}
              >
                {agentsLoading ? "생성 중..." : "생성"}
              </button>
            </div>

            {agentsError && (
              <div
                style={{
                  marginTop: "15px",
                  padding: "10px",
                  background: "var(--red)",
                  borderRadius: "4px",
                  color: "white",
                }}
              >
                {agentsError}
              </div>
            )}

            {agentsContent && (
              <div style={{ marginTop: "30px" }}>
                <div
                  style={{
                    display: "flex",
                    gap: "10px",
                    marginBottom: "15px",
                  }}
                >
                  <button
                    onClick={downloadAgents}
                    style={{
                      padding: "10px 20px",
                      background: "var(--green)",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    다운로드
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(agentsContent)
                      alert("클립보드에 복사되었습니다")
                    }}
                    style={{
                      padding: "10px 20px",
                      background: "var(--accent)",
                      color: "white",
                      border: "none",
                      borderRadius: "4px",
                      cursor: "pointer",
                    }}
                  >
                    복사
                  </button>
                </div>
                <textarea
                  value={agentsContent}
                  readOnly
                  style={{
                    width: "100%",
                    padding: "15px",
                    background: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "4px",
                    color: "var(--text)",
                    minHeight: "500px",
                    fontFamily: "monospace",
                    fontSize: "12px",
                  }}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
