'use client'

import { useState } from 'react'

const API_BASE = 'http://localhost:8000'

type Teammate = {
  v_id: string
  v_name: string
}

type MyTask = {
  task_id: string
  task_name: string
  time_start: string
  time_end: string
  location: string
  detail: string
  '1st_lead': string
  '2nd_lead': string
  teammates: Teammate[]
}

type VolunteerData = {
  v_id: string
  v_name: string
  my_tasks: MyTask[]
}

export default function VolunteerPage() {
  const [vId, setVId] = useState('')
  const [data, setData] = useState<VolunteerData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function fetchMyTasks() {
    if (!vId.trim()) {
      setError('请输入你的 Volunteer ID')
      return
    }
    setLoading(true)
    setError('')
    setData(null)
    try {
      const res = await fetch(`${API_BASE}/volunteer/${vId.trim().toUpperCase()}`)
      if (res.status === 404) {
        setError(`找不到 ID 为 "${vId}" 的 volunteer，请确认 ID 是否正确`)
        return
      }
      const json = await res.json()
      setData(json)
    } catch {
      setError('无法连接到服务器，请稍后再试')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-2xl mx-auto">

        {/* 页头 */}
        <div className="mb-8">
          <h1 className="text-2xl font-semibold text-gray-900">我的任务</h1>
          <p className="text-gray-500 mt-1 text-sm">输入你的 Volunteer ID 查看排班安排</p>
        </div>

        {/* 输入框 */}
        <div className="flex gap-3 mb-6">
          <input
            type="text"
            placeholder="输入 Volunteer ID，例如 V001"
            value={vId}
            onChange={e => setVId(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchMyTasks()}
            className="flex-1 px-4 py-2.5 border border-gray-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-gray-300 bg-white"
          />
          <button
            onClick={fetchMyTasks}
            disabled={loading}
            className="px-5 py-2.5 bg-gray-900 text-white rounded-lg text-sm font-medium hover:bg-gray-700 disabled:opacity-50 transition"
          >
            {loading ? '查询中...' : '查询'}
          </button>
        </div>

        {/* 错误提示 */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        {/* 个人信息 + 任务 */}
        {data && (
          <div>
            {/* 欢迎语 */}
            <div className="mb-6 p-4 bg-gray-900 rounded-xl text-white">
              <p className="text-xs text-gray-400 mb-0.5">你好</p>
              <p className="text-xl font-semibold">{data.v_name}</p>
              <p className="text-sm text-gray-400 mt-1">
                本次活动共分配了 {data.my_tasks?.length ?? 0} 个任务给你
              </p>
            </div>

            {/* 任务列表 */}
            {(data.my_tasks ?? []).length === 0 ? (
              <div className="bg-white border border-gray-200 rounded-xl p-6 text-center text-gray-400 text-sm">
                暂时没有分配任务给你，请联系 Organizer 确认
              </div>
            ) : (
              <div className="space-y-4">
                {(data.my_tasks ?? []).map(task => (
                  <div key={task.task_id} className="bg-white border border-gray-200 rounded-xl p-5">

                    {/* 任务名 + 时间 */}
                    <div className="mb-4">
                      <h2 className="text-base font-semibold text-gray-900">{task.task_name}</h2>
                      <p className="text-xs text-gray-400 mt-0.5">
                        {task.time_start} – {task.time_end}
                        {task.location && ` · ${task.location}`}
                      </p>
                    </div>

                    {/* 任务说明 */}
                    {task.detail && (
                      <div className="mb-4 p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-400 mb-1">任务说明</p>
                        <p className="text-sm text-gray-700 leading-relaxed">{task.detail}</p>
                      </div>
                    )}

                    <div className="grid grid-cols-2 gap-3">
                      {/* 负责人 */}
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-400 mb-2">遇到问题找谁</p>
                        <div className="space-y-1.5">
                          {task['1st_lead'] && (
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full bg-gray-800 flex items-center justify-center text-white text-xs">
                                {task['1st_lead'][0]}
                              </div>
                              <span className="text-sm text-gray-700">{task['1st_lead']}</span>
                              <span className="text-xs text-gray-400">负责人</span>
                            </div>
                          )}
                          {task['2nd_lead'] && (
                            <div className="flex items-center gap-2">
                              <div className="w-6 h-6 rounded-full bg-gray-400 flex items-center justify-center text-white text-xs">
                                {task['2nd_lead'][0]}
                              </div>
                              <span className="text-sm text-gray-700">{task['2nd_lead']}</span>
                              <span className="text-xs text-gray-400">副负责人</span>
                            </div>
                          )}
                        </div>
                      </div>

                      {/* 队友 */}
                      <div className="p-3 bg-gray-50 rounded-lg">
                        <p className="text-xs text-gray-400 mb-2">你的队友</p>
                        {task.teammates.length === 0 ? (
                          <p className="text-sm text-gray-400">你是这个任务唯一的负责人</p>
                        ) : (
                          <div className="space-y-1.5">
                            {task.teammates.map(t => (
                              <div key={t.v_id} className="flex items-center gap-2">
                                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center text-blue-700 text-xs font-medium">
                                  {t.v_name[0]}
                                </div>
                                <span className="text-sm text-gray-700">{t.v_name}</span>
                                <span className="text-xs text-gray-400">{t.v_id}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                  </div>
                ))}
              </div>
            )}
          </div>
        )}

      </div>
    </main>
  )
}