import { useState } from 'react';
import { FileCheck, Users, ArrowRight, Sparkles } from 'lucide-react';
import { motion } from 'motion/react';

interface ServiceHubProps {
  onSelectService: (service: 'contract' | 'roommate') => void;
}

/**
 * 服务中心 - 统一功能入口页面
 * 提供合同审查和合租伙伴匹配两个核心功能的入口
 */
export const ServiceHub = ({ onSelectService }: ServiceHubProps) => {
  const [hoveredService, setHoveredService] = useState<string | null>(null);

  const services = [
    {
      id: 'contract' as const,
      title: '合同智能审查',
      subtitle: '🦉 AI 四重审查',
      description: '猫头鹰、猎犬、海狸、小猫四位智能体协同工作，全方位审查租房合同',
      features: [
        '霸王条款识别',
        '法律法规匹配',
        '费用核算验证',
        '风险等级评估'
      ],
      icon: FileCheck,
      color: 'bg-accent',
      borderColor: 'border-accent',
      hoverShadow: 'hover:shadow-[12px_12px_0px_var(--color-accent)]'
    },
    {
      id: 'roommate' as const,
      title: '合租伙伴匹配',
      subtitle: '🐾 宠物代理面试',
      description: '电子宠物先行面试，识别生活习惯差异，避免合租矛盾',
      features: [
        '生活习惯分析',
        '踩雷点识别',
        '智能匹配推荐',
        '实时对话监控'
      ],
      icon: Users,
      color: 'bg-primary',
      borderColor: 'border-primary',
      hoverShadow: 'hover:shadow-[12px_12px_0px_var(--color-primary)]'
    }
  ];

  return (
    <div className="min-h-screen bg-surface-alt flex items-center justify-center p-4 sm:p-8">
      <div className="max-w-6xl w-full">
        {/* 标题区域 */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="inline-flex items-center gap-3 mb-4">
            <div className="w-16 h-16 bg-secondary border-4 border-ink rounded-2xl flex items-center justify-center text-3xl shadow-[4px_4px_0px_var(--color-ink)] transform -rotate-6">
              🐾
            </div>
            <h1 className="text-4xl sm:text-5xl font-black text-ink">
              租房避坑局
            </h1>
          </div>
          <p className="text-lg font-bold text-gray-custom">
            AI 智能助手，让租房更安心
          </p>
        </motion.div>

        {/* 服务卡片网格 */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {services.map((service, index) => {
            const Icon = service.icon;
            const isHovered = hoveredService === service.id;

            return (
              <motion.div
                key={service.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
                onMouseEnter={() => setHoveredService(service.id)}
                onMouseLeave={() => setHoveredService(null)}
                onClick={() => onSelectService(service.id)}
                className={`
                  bg-surface border-4 border-ink rounded-3xl p-8
                  shadow-[8px_8px_0px_var(--color-ink)]
                  ${service.hoverShadow}
                  transition-all duration-300 cursor-pointer
                  transform hover:scale-105
                  relative overflow-hidden
                `}
              >
                {/* 背景装饰 */}
                <div className={`absolute top-0 right-0 w-32 h-32 ${service.color} opacity-10 rounded-full blur-3xl`}></div>

                {/* 图标和标题 */}
                <div className="relative z-10">
                  <div className="flex items-start justify-between mb-6">
                    <div className={`
                      w-16 h-16 ${service.color} border-4 border-ink rounded-2xl
                      flex items-center justify-center
                      shadow-[4px_4px_0px_var(--color-ink)]
                      transform ${isHovered ? 'rotate-6 scale-110' : 'rotate-0'}
                      transition-all duration-300
                    `}>
                      <Icon size={32} className="text-ink" strokeWidth={2.5} />
                    </div>
                    <motion.div
                      animate={{ x: isHovered ? 5 : 0 }}
                      transition={{ duration: 0.3 }}
                    >
                      <ArrowRight size={32} className="text-ink" strokeWidth={2.5} />
                    </motion.div>
                  </div>

                  <h2 className="text-2xl font-black text-ink mb-2">
                    {service.title}
                  </h2>
                  <p className="text-sm font-bold text-gray-custom mb-4">
                    {service.subtitle}
                  </p>
                  <p className="text-base font-bold text-ink/80 mb-6">
                    {service.description}
                  </p>

                  {/* 功能列表 */}
                  <div className="space-y-3">
                    {service.features.map((feature, idx) => (
                      <motion.div
                        key={idx}
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: index * 0.1 + idx * 0.05 }}
                        className="flex items-center gap-3"
                      >
                        <div className={`
                          w-6 h-6 ${service.color} border-2 border-ink rounded-lg
                          flex items-center justify-center
                          shadow-[2px_2px_0px_var(--color-ink)]
                        `}>
                          <Sparkles size={14} className="text-ink" />
                        </div>
                        <span className="text-sm font-black text-ink">
                          {feature}
                        </span>
                      </motion.div>
                    ))}
                  </div>

                  {/* 点击提示 */}
                  <motion.div
                    animate={{ opacity: isHovered ? 1 : 0 }}
                    className="mt-6 text-center"
                  >
                    <span className="inline-block px-4 py-2 bg-ink text-surface rounded-xl font-black text-sm">
                      点击进入 →
                    </span>
                  </motion.div>
                </div>
              </motion.div>
            );
          })}
        </div>

        {/* 底部说明 */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-12 text-center"
        >
          <div className="inline-block bg-paper border-4 border-ink rounded-2xl px-6 py-4 shadow-[4px_4px_0px_var(--color-ink)]">
            <p className="text-sm font-bold text-gray-custom">
              💡 提示：两个功能可以独立使用，也可以配合使用获得更好的租房体验
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
