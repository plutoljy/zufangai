/**
 * 合租匹配 API 服务 - MVP 版本
 */

const API_BASE = `http://localhost:${import.meta.env.VITE_API_PORT || 8010}`;

export interface LifestyleData {
  sleep_time: string;
  cleanliness: number;
  social_level: number;
  noise_level: number;
  smoking: boolean;
  pets: boolean;
  deal_breakers: string[];
}

export interface RequestData {
  title: string;
  location: string;
  rent_min: number;
  rent_max: number;
  mode: string;
}

export const RoommateAPI = {
  // 创建宠物画像
  async createProfile(data: LifestyleData) {
    const res = await fetch(`${API_BASE}/api/roommate/profile`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create profile');
    return res.json();
  },

  // 发布合租需求
  async createRequest(data: RequestData) {
    const res = await fetch(`${API_BASE}/api/roommate/request`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create request');
    return res.json();
  },

  // 获取候选人列表
  async getCandidates() {
    const res = await fetch(`${API_BASE}/api/roommate/candidates`);
    if (!res.ok) throw new Error('Failed to get candidates');
    return res.json();
  },

  // 获取面试详情
  async getInterview(candidateId: string) {
    const res = await fetch(`${API_BASE}/api/roommate/interview/${candidateId}`);
    if (!res.ok) throw new Error('Failed to get interview');
    return res.json();
  },

  // 发送房东插入消息
  async sendInterruptMessage(candidateId: string, message: any) {
    const res = await fetch(`${API_BASE}/api/roommate/interview/${candidateId}/interrupt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(message),
    });
    if (!res.ok) throw new Error('Failed to send interrupt message');
    return res.json();
  },
};
