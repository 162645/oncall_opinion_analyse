/**
 * 思考进度指示器
 * 支持长时间思考的进度展示
 */
import { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Progress,
  Space,
  Tag,
  Spin,
} from '@douyinfe/semi-ui'
import {
  IconBulb,
  IconClock,
  IconSearch,
  IconStar,
  IconServer,
  IconPulse,
} from '@douyinfe/semi-icons'
import './ThinkingProgress.css'

const { Text } = Typography

interface ThinkingStage {
  id: string
  name: string
  description: string
  icon: React.ReactNode
  status: 'pending' | 'active' | 'completed'
  duration_ms?: number
}

interface ThinkingProgressProps {
  stages?: ThinkingStage[]
  startTime: Date
  estimatedDuration?: number
  isThinking: boolean
  thinkingContent?: string
}

// 预设阶段
const defaultStages: ThinkingStage[] = [
  { id: 'understand', name: '理解问题', description: '分析用户意图', icon: <IconBulb />, status: 'pending' },
  { id: 'retrieve', name: '检索知识', description: '查询相关知识', icon: <IconSearch />, status: 'pending' },
  { id: 'query', name: '查询数据', description: '获取网络数据', icon: <IconServer />, status: 'pending' },
  { id: 'analyze', name: '分析处理', description: '处理分析结果', icon: <IconPulse />, status: 'pending' },
  { id: 'generate', name: '生成回答', description: '组织最终答案', icon: <IconStar />, status: 'pending' },
]

function ThinkingProgress({
  stages = defaultStages,
  startTime,
  isThinking,
}: ThinkingProgressProps) {
  const [elapsedTime, setElapsedTime] = useState(0)
  const [currentStageIndex, setCurrentStageIndex] = useState(0)

  // 实时计时
  useEffect(() => {
    if (isThinking) {
      const interval = setInterval(() => {
        setElapsedTime(Date.now() - startTime.getTime())
      }, 100)
      return () => clearInterval(interval)
    } else {
      setElapsedTime(0)
    }
  }, [isThinking, startTime])

  // 阶段自动推进 - 根据时间平滑推进
  useEffect(() => {
    if (!isThinking) {
      setCurrentStageIndex(0)
      return
    }

    // 每个阶段大约 2-4 秒
    const stageDurations = [2000, 3000, 4000, 3000, 2000]

    const interval = setInterval(() => {
      const currentElapsed = Date.now() - startTime.getTime()

      // 根据经过时间计算应该在哪个阶段
      let accumulated = 0
      for (let i = 0; i < stageDurations.length; i++) {
        accumulated += stageDurations[i]
        if (currentElapsed < accumulated) {
          setCurrentStageIndex(i)
          return
        }
      }
      // 如果超过总时间，保持在最后一个阶段
      setCurrentStageIndex(stageDurations.length - 1)
    }, 200)

    return () => clearInterval(interval)
  }, [isThinking, startTime])

  // 格式化时间
  const formatTime = (ms: number): string => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.round((ms % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }

  // 获取阶段状态样式
  const getStageStatus = (index: number): 'pending' | 'active' | 'completed' => {
    if (index < currentStageIndex) return 'completed'
    if (index === currentStageIndex) return 'active'
    return 'pending'
  }

  // 计算进度百分比 - 更平滑的进度
  const progressPercent = Math.min(
    ((currentStageIndex + 0.5) / stages.length) * 100,
    95
  )

  return (
    <Card className="thinking-progress-card" style={{ padding: 12 }}>
      <div className="progress-header" style={{ marginBottom: 8 }}>
        <Space>
          <Spin size="small" />
          <Text strong>正在思考</Text>
        </Space>
        <Space>
          <IconClock style={{ color: 'var(--semi-color-primary)' }} />
          <Text strong style={{ fontSize: 15, color: 'var(--semi-color-primary)' }}>
            {formatTime(elapsedTime)}
          </Text>
        </Space>
      </div>

      {/* 进度条 */}
      <Progress
        percent={progressPercent}
        showInfo
        stroke="var(--semi-color-primary)"
        style={{ marginBottom: 8 }}
        size="small"
      />

      {/* 思考阶段 - 紧凑布局 */}
      <div className="stages-container" style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {stages.map((stage, index) => {
          const status = getStageStatus(index)
          const isActive = status === 'active'
          const isCompleted = status === 'completed'

          return (
            <Tag
              key={stage.id}
              size="small"
              color={isCompleted ? 'green' : isActive ? 'blue' : 'grey'}
              style={{
                opacity: status === 'pending' ? 0.5 : 1,
                padding: '2px 8px',
              }}
            >
              {isCompleted ? '✓' : isActive ? <Spin size="small" /> : stage.icon}
              <span style={{ marginLeft: 4 }}>{stage.name}</span>
            </Tag>
          )
        })}
      </div>

      {/* 提示信息 */}
      <Text type="tertiary" size="small" style={{ display: 'block', marginTop: 8 }}>
        💡 AI 正在分析问题，请稍候...
      </Text>
    </Card>
  )
}

export default ThinkingProgress
