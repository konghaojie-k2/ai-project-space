'use client'

import { forwardRef, ReactNode } from 'react'
import { UseFormRegister, FieldError, UseFormWatch } from 'react-hook-form'
import { clsx } from 'clsx'
import { ExclamationCircleIcon, CheckCircleIcon } from '@heroicons/react/24/outline'

interface FormFieldProps {
  label: string
  name: string
  type?: 'text' | 'email' | 'password' | 'tel' | 'url' | 'number' | 'textarea'
  placeholder?: string
  register: UseFormRegister<any>
  error?: FieldError
  helperText?: string
  required?: boolean
  disabled?: boolean
  className?: string
  rows?: number
  leftIcon?: ReactNode
  rightIcon?: ReactNode
  autoComplete?: string
  maxLength?: number
  showSuccess?: boolean
  watch?: UseFormWatch<any>
}

const FormField = forwardRef<HTMLInputElement | HTMLTextAreaElement, FormFieldProps>(
  ({
    label,
    name,
    type = 'text',
    placeholder,
    register,
    error,
    helperText,
    required = false,
    disabled = false,
    className,
    rows = 3,
    leftIcon,
    rightIcon,
    autoComplete,
    maxLength,
    showSuccess = false,
    watch,
    ...props
  }, ref) => {
    const isTextarea = type === 'textarea'
    const hasError = !!error
    const value = watch?.(name) || ''
    const hasValue = value && value.length > 0
    const showSuccessIcon = showSuccess && hasValue && !hasError

    const inputClasses = clsx(
      'block w-full rounded-lg border-0 py-2.5 px-3 text-gray-900 shadow-sm ring-1 ring-inset placeholder:text-gray-400 focus:ring-2 focus:ring-inset sm:text-sm sm:leading-6 transition-colors',
      {
        // 默认状态
        'ring-gray-300 focus:ring-blue-600': !hasError && !showSuccessIcon,
        // 错误状态
        'ring-red-300 focus:ring-red-500 text-red-900 placeholder:text-red-300': hasError,
        // 成功状态
        'ring-green-300 focus:ring-green-500': showSuccessIcon,
        // 禁用状态
        'disabled:cursor-not-allowed disabled:bg-gray-50 disabled:text-gray-500 disabled:ring-gray-200': disabled,
        // 左图标间距
        'pl-10': leftIcon,
        // 右图标间距
        'pr-10': rightIcon || hasError || showSuccessIcon,
      },
      className
    )

    const InputComponent = isTextarea ? 'textarea' : 'input'

    return (
      <div className="space-y-2">
        {/* 标签 */}
        <label htmlFor={name} className="block text-sm font-medium leading-6 text-gray-900">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>

        {/* 输入框容器 */}
        <div className="relative">
          {/* 左图标 */}
          {leftIcon && (
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <div className="h-5 w-5 text-gray-400">
                {leftIcon}
              </div>
            </div>
          )}

          {/* 输入框 */}
          <InputComponent
            id={name}
            {...register(name)}
            type={isTextarea ? undefined : type}
            placeholder={placeholder}
            className={inputClasses}
            disabled={disabled}
            autoComplete={autoComplete}
            maxLength={maxLength}
            rows={isTextarea ? rows : undefined}
            ref={ref as any}
            {...props}
          />

          {/* 右图标 */}
          <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3">
            {hasError && (
              <ExclamationCircleIcon className="h-5 w-5 text-red-500" />
            )}
            {showSuccessIcon && (
              <CheckCircleIcon className="h-5 w-5 text-green-500" />
            )}
            {rightIcon && !hasError && !showSuccessIcon && (
              <div className="h-5 w-5 text-gray-400">
                {rightIcon}
              </div>
            )}
          </div>
        </div>

        {/* 帮助文本和错误信息 */}
        <div className="min-h-[1.25rem]">
          {hasError ? (
            <p className="text-sm text-red-600 flex items-center">
              <ExclamationCircleIcon className="h-4 w-4 mr-1 flex-shrink-0" />
              {error.message}
            </p>
          ) : helperText ? (
            <p className="text-sm text-gray-600">{helperText}</p>
          ) : null}
        </div>

        {/* 字符计数 */}
        {maxLength && (
          <div className="text-right">
            <span className={clsx(
              'text-xs',
              value.length > maxLength * 0.8 ? 'text-orange-600' : 'text-gray-500'
            )}>
              {value.length}/{maxLength}
            </span>
          </div>
        )}
      </div>
    )
  }
)

FormField.displayName = 'FormField'

export default FormField 