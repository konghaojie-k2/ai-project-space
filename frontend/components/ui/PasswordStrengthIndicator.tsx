'use client'

import { clsx } from 'clsx'
import { CheckCircleIcon, XCircleIcon } from '@heroicons/react/24/outline'
import { checkPasswordStrength } from '@/lib/validations'

interface PasswordStrengthIndicatorProps {
  password: string
  className?: string
}

const PasswordStrengthIndicator = ({ password, className }: PasswordStrengthIndicatorProps) => {
  const { score, feedback, isValid } = checkPasswordStrength(password)

  // 如果密码为空，不显示指示器
  if (!password) {
    return null
  }

  const strengthLevels = [
    { label: '很弱', color: 'bg-red-500', textColor: 'text-red-600' },
    { label: '弱', color: 'bg-orange-500', textColor: 'text-orange-600' },
    { label: '一般', color: 'bg-yellow-500', textColor: 'text-yellow-600' },
    { label: '强', color: 'bg-blue-500', textColor: 'text-blue-600' },
    { label: '很强', color: 'bg-green-500', textColor: 'text-green-600' },
  ]

  const currentLevel = strengthLevels[score - 1] || strengthLevels[0]

  return (
    <div className={clsx('space-y-3', className)}>
      {/* 强度条 */}
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">密码强度</span>
          <span className={clsx('text-sm font-medium', currentLevel.textColor)}>
            {currentLevel.label}
          </span>
        </div>
        
        <div className="flex space-x-1">
          {strengthLevels.map((level, index) => (
            <div
              key={index}
              className={clsx(
                'h-2 flex-1 rounded-full transition-colors duration-200',
                index < score ? level.color : 'bg-gray-200'
              )}
            />
          ))}
        </div>
      </div>

      {/* 密码要求检查 */}
      {feedback.length > 0 && (
        <div className="space-y-1">
          <span className="text-sm font-medium text-gray-700">密码要求：</span>
          <ul className="space-y-1">
            {[
              { requirement: '至少8个字符', met: password.length >= 8 },
              { requirement: '包含大写字母', met: /[A-Z]/.test(password) },
              { requirement: '包含小写字母', met: /[a-z]/.test(password) },
              { requirement: '包含数字', met: /\d/.test(password) },
              { requirement: '包含特殊字符', met: /[@$!%*?&]/.test(password) },
            ].map((item, index) => (
              <li key={index} className="flex items-center space-x-2">
                {item.met ? (
                  <CheckCircleIcon className="h-4 w-4 text-green-500 flex-shrink-0" />
                ) : (
                  <XCircleIcon className="h-4 w-4 text-gray-400 flex-shrink-0" />
                )}
                <span className={clsx(
                  'text-sm',
                  item.met ? 'text-green-600' : 'text-gray-600'
                )}>
                  {item.requirement}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* 整体状态 */}
      {isValid && (
        <div className="flex items-center space-x-2 text-green-600">
          <CheckCircleIcon className="h-4 w-4" />
          <span className="text-sm font-medium">密码强度符合要求</span>
        </div>
      )}
    </div>
  )
}

export default PasswordStrengthIndicator 