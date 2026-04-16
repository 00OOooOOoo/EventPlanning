'use client'

import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

type Volunteer = {
  v_id: string
  v_name: string
  skill_match: number
  preference_score: number
  unwilling_score: number
}

type TaskResult = {
  task_id: string
  task_name: string
  time_start: string
  time_end: string
  staff_num: number
  assigned: Volunteer[]
  understaffed: number
  status: string
  '1st_lead': string
  '2nd_lead': string
}

export default function OrganizerPage() {
  const [results, setResults] = useState<TaskResult[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [ran, setRan] = useState(false)

  async function runMatching() {
    setLoading(true)
    setError('')
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 120000) // 等待最多 2 分钟

      const res = await fetch(`${API_BASE}/run-matching`, {
        method: 'POST',
        signal: controller.signal
      })
      clearTimeout(timeoutId)

      const data = await res.json()
      if (data.status === 'success') {
        setResults(data.results)
        setRan(true)
      } else {
        setError('排班失败，请检查数据')
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === 'AbortError') {
        setError('计算超时，请重试')
      } else {
        setError('无法连接到后端服务，请确认 uvicorn 正在运行')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">

      {/* 页头 */}
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">排班管理</h1>
          <p className="text-gray-500 mt-1 text-sm">Organizer 视角 — 生成并查看志愿者排班结果</p>
        </div>

        {/* 触发按钮 */}
        <button
          onClick={runMatching}
          disabled={loading}
          className="mb-8 px-6 py-3 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 transition"
        >
          {loading ? '排班计算中...' : '生成排班方案'}
        </button>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* 排班结果 */}
        {ran && results.length > 0 && (
          <div className="space-y-4">

            {/* 顶部统计 */}
            <div className="grid grid-cols-3 gap-4 mb-6">
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-400 mb-1">任务总数</p>
                <p className="text-2xl font-semibold text-gray-900">{results.length}</p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-400 mb-1">已满员</p>
                <p className="text-2xl font-semibold text-green-600">
                  {results.filter(r => r.status === 'ok').length}
                </p>
              </div>
              <div className="bg-white rounded-xl border border-gray-200 p-4">
                <p className="text-xs text-gray-400 mb-1">需要补人</p>
                <p className="text-2xl font-semibold text-red-500">
                  {results.filter(r => r.status === 'understaffed').length}
                </p>
              </div>
            </div>

            {/* 每个任务的卡片 */}
            {results.map(task => (
              <div
                key={task.task_id}
                className={`bg-white rounded-xl border p-5 ${
                  task.status === 'understaffed'
                    ? 'border-red-300 bg-red-50'
                    : 'border-gray-200'
                }`}
              >
                {/* 任务标题行 */}
                <div className="flex items-start justify-between mb-3">
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-base font-semibold text-gray-900">
                        {task.task_name}
                      </h2>
                      {task.status === 'understaffed' && (
                        <span className="text-xs bg-red-100 text-red-600 px-2 py-0.5 rounded-full">
                          缺 {task.understaffed} 人
                        </span>
                      )}
                      {task.status === 'ok' && (
                        <span className="text-xs bg-green-100 text-green-600 px-2 py-0.5 rounded-full">
                          已满员
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-gray-400 mt-0.5">
                      {task.time_start} – {task.time_end} · 需要 {task.staff_num} 人
                    </p>
                  </div>
                  <div className="text-right text-xs text-gray-400">
                    <p>负责人：{task['1st_lead'] || '未设置'}</p>
                    {task['2nd_lead'] && <p>副负责人：{task['2nd_lead']}</p>}
                  </div>
                </div>

                {/* 分配的 volunteer */}
                {task.assigned.length > 0 ? (
                  <div className="space-y-2">
                    {task.assigned.map(v => (
                      <div
                        key={v.v_id}
                        className="flex items-center justify-between bg-gray-50 rounded-lg px-4 py-2.5"
                      >
                        <div className="flex items-center gap-3">
                          {/* 头像占位 */}
                          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium text-gray-600">
                            {v.v_name[0]}
                          </div>
                          <span className="text-sm font-medium text-gray-800">
                            {v.v_name}
                          </span>
                          <span className="text-xs text-gray-400">{v.v_id}</span>
                        </div>
                        {/* 匹配分数 */}
                        <div className="flex gap-3 text-xs text-gray-400">
                          <span>技能 {(v.skill_match * 100).toFixed(0)}%</span>
                          <span>偏好 {(v.preference_score * 100).toFixed(0)}%</span>
                          {v.unwilling_score > 0.1 && (
                            <span className="text-orange-400">
                              排斥 {(v.unwilling_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-sm text-red-400">暂无人员分配</p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  )
}