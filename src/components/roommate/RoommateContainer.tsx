/**
 * 合租匹配主容器 - 完整版
 * 管理整个合租匹配流程的状态和导航
 */
import React, { useState, useEffect } from 'react';
import { RoleSelection } from './RoleSelection';
import { PetSelection } from './PetSelection';
import { LifestyleForm } from './LifestyleForm';
import { RequestForm } from './RequestForm';
import { CandidateList } from './CandidateList';
import { InterviewView } from './InterviewView';
import { RoommateAPI } from '../../services/roommateAPI';

type RoommateView = 'role' | 'pet' | 'lifestyle' | 'request' | 'candidates' | 'interview';

interface Props {
  onBack: () => void;
}

export const RoommateContainer: React.FC<Props> = ({ onBack }) => {
  const [currentView, setCurrentView] = useState<RoommateView>('role');
  const [userRole, setUserRole] = useState<'landlord' | 'tenant' | null>(null);
  const [petInfo, setPetInfo] = useState<any>(null);
  const [selectedCandidateId, setSelectedCandidateId] = useState<string | null>(null);
  const [candidates, setCandidates] = useState<any[]>([]);
  const [interviewData, setInterviewData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);  // 新增：消息列表状态

  const handleRoleSelect = (role: 'landlord' | 'tenant') => {
    setUserRole(role);
    setCurrentView('pet');
  };

  const handlePetSubmit = (pet: any) => {
    setPetInfo(pet);
    setCurrentView('lifestyle');
  };

  const handleLifestyleSubmit = async (data: any) => {
    try {
      setLoading(true);
      // 转换字段名：驼峰 -> 下划线
      const apiData = {
        sleep_time: data.sleepTime,
        cleanliness: data.cleanliness,
        social_level: data.socialLevel,
        noise_level: data.noiseLevel,
        smoking: data.smoking,
        pets: data.pets,
        deal_breakers: data.dealBreakers,
      };
      await RoommateAPI.createProfile(apiData);
      setCurrentView('request');
    } catch (error) {
      console.error('创建画像失败:', error);
      alert('创建画像失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestSubmit = async (data: any) => {
    try {
      setLoading(true);
      console.log('[handleRequestSubmit] 开始发布需求，数据:', data);

      // 转换字段名：驼峰 -> 下划线
      const apiData = {
        title: data.title,
        location: data.location,
        rent_min: data.rentMin,
        rent_max: data.rentMax,
        mode: data.mode,
      };
      console.log('[handleRequestSubmit] API数据:', apiData);

      await RoommateAPI.createRequest(apiData);
      console.log('[handleRequestSubmit] 需求创建成功，获取候选人列表');

      const candidatesData = await RoommateAPI.getCandidates();
      console.log('[handleRequestSubmit] 候选人数据:', candidatesData);

      setCandidates(candidatesData);
      setCurrentView('candidates');
      console.log('[handleRequestSubmit] 切换到候选人列表视图');
    } catch (error) {
      console.error('[handleRequestSubmit] 发布需求失败:', error);
      alert('发布需求失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleViewInterview = async (candidateId: string) => {
    try {
      setLoading(true);
      const data = await RoommateAPI.getInterview(candidateId);
      setInterviewData(data);
      setMessages(data.messages || []);  // 初始化消息列表
      setSelectedCandidateId(candidateId);
      setCurrentView('interview');
    } catch (error) {
      console.error('获取面试数据失败:', error);
      alert('获取面试数据失败，请重试');
    } finally {
      setLoading(false);
    }
  };

  const handleSendInterrupt = async (message: any) => {
    try {
      // 乐观更新UI
      setMessages(prev => [...prev, message]);

      // 调用API发送消息
      if (selectedCandidateId) {
        await RoommateAPI.sendInterruptMessage(selectedCandidateId, message);
      }
    } catch (error) {
      console.error('发送消息失败:', error);
      // 回滚UI更新
      setMessages(prev => prev.filter(m => m.id !== message.id));
      throw error;
    }
  };

  const handleBackFromInterview = () => {
    setCurrentView('candidates');
    setSelectedCandidateId(null);
    setInterviewData(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin text-6xl mb-4">{petInfo?.avatar || '🐾'}</div>
          <p className="text-lg font-bold">加载中...</p>
        </div>
      </div>
    );
  }

  return (
    <>
      {currentView === 'role' && (
        <RoleSelection onSelect={handleRoleSelect} onBack={onBack} />
      )}
      {currentView === 'pet' && (
        <PetSelection onSubmit={handlePetSubmit} onBack={() => setCurrentView('role')} />
      )}
      {currentView === 'lifestyle' && (
        <LifestyleForm onSubmit={handleLifestyleSubmit} onBack={() => setCurrentView('pet')} />
      )}
      {currentView === 'request' && (
        <RequestForm onSubmit={handleRequestSubmit} onBack={() => setCurrentView('lifestyle')} />
      )}
      {currentView === 'candidates' && (
        <CandidateList
          candidates={candidates}
          onViewInterview={handleViewInterview}
          onBack={() => setCurrentView('request')}
        />
      )}
      {currentView === 'interview' && interviewData && (
        <InterviewView
          candidateName={interviewData.candidateName}
          candidateId={selectedCandidateId || undefined}
          messages={messages}
          matchResult={interviewData.matchResult}
          onBack={handleBackFromInterview}
          onSendInterrupt={handleSendInterrupt}
        />
      )}
    </>
  );
};
