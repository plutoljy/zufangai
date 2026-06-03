/**
 * 候选人列表 - MVP 版本
 */
import React from 'react';
import { motion } from 'framer-motion';
import { Users, MessageCircle, TrendingUp } from 'lucide-react';

interface Candidate {
  id: string;
  name: string;
  matchScore: number;
  avatar: string;
  lifestyle: {
    sleepTime: string;
    cleanliness: number;
    socialLevel: number;
  };
  dealBreakers: string[];
  interviewStatus: 'pending' | 'in_progress' | 'completed';
}

interface Props {
  candidates: Candidate[];
  onViewInterview: (candidateId: string) => void;
  onBack: () => void;
}

export const CandidateList: React.FC<Props> = ({ candidates, onViewInterview, onBack }) => {
  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getStatusText = (status: string) => {
    const map = {
      pending: '⏳ 等待面试',
      in_progress: '💬 面试中',
      completed: '✅ 已完成',
    };
    return map[status as keyof typeof map] || status;
  };

  return (
    <div className="min-h-screen bg-background p-6">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="max-w-4xl mx-auto"
      >
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold mb-2">👥 候选人列表</h1>
            <p className="text-muted-foreground">共 {candidates.length} 位候选人</p>
          </div>
          <button
            onClick={onBack}
            className="px-6 py-3 bg-muted rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
          >
            返回
          </button>
        </div>

        <div className="space-y-4">
          {candidates.map((candidate, index) => (
            <motion.div
              key={candidate.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-card p-6 rounded-lg border-4 border-border shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all"
            >
              <div className="flex items-start gap-4">
                {/* 头像 */}
                <div className="w-16 h-16 rounded-full bg-primary/20 flex items-center justify-center text-2xl border-4 border-border">
                  {candidate.avatar}
                </div>

                {/* 信息 */}
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-xl font-bold">{candidate.name}</h3>
                    <div className="flex items-center gap-2">
                      <TrendingUp className="w-5 h-5" />
                      <span className={`text-2xl font-bold ${getScoreColor(candidate.matchScore)}`}>
                        {candidate.matchScore}%
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 mb-3 text-sm">
                    <div>
                      <span className="text-muted-foreground">作息：</span>
                      <span className="font-medium">{candidate.lifestyle.sleepTime}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">清洁：</span>
                      <span className="font-medium">{candidate.lifestyle.cleanliness}/5</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">社交：</span>
                      <span className="font-medium">{candidate.lifestyle.socialLevel}/5</span>
                    </div>
                  </div>

                  {candidate.dealBreakers.length > 0 && (
                    <div className="mb-3">
                      <span className="text-sm text-muted-foreground">踩雷点：</span>
                      <div className="flex flex-wrap gap-2 mt-1">
                        {candidate.dealBreakers.map(item => (
                          <span
                            key={item}
                            className="px-2 py-1 text-xs bg-destructive/20 text-destructive rounded border border-destructive"
                          >
                            {item}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{getStatusText(candidate.interviewStatus)}</span>
                    <button
                      onClick={() => onViewInterview(candidate.id)}
                      disabled={candidate.interviewStatus === 'pending'}
                      className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg border-2 border-border hover:translate-x-0.5 hover:translate-y-0.5 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <MessageCircle className="w-4 h-4" />
                      查看面试
                    </button>
                  </div>
                </div>
              </div>
            </motion.div>
          ))}
        </div>

        {candidates.length === 0 && (
          <div className="text-center py-12 bg-card rounded-lg border-4 border-border">
            <Users className="w-16 h-16 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg text-muted-foreground">暂无候选人</p>
          </div>
        )}
      </motion.div>
    </div>
  );
};
