import type { AuthChangeEvent, Session, User } from '@supabase/supabase-js';

import { supabase } from './supabase';

export interface RentalProfile {
  id: string;
  username: string;
  email: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface AuthCredentials {
  email: string;
  password: string;
}

export interface RegisterCredentials extends AuthCredentials {
  username: string;
}

function normalizeAuthErrorMessage(message: string) {
  if (message.includes('rental_profiles_username_key')) {
    return '这个用户名已经被占用了，请换一个试试。';
  }
  if (message.includes('User already registered')) {
    return '这个邮箱已经注册过了，直接登录就可以。';
  }
  if (message.includes('Invalid login credentials')) {
    return '邮箱或密码不正确。';
  }
  return message;
}

async function upsertProfile(user: User, username?: string) {
  const nextUsername =
    username?.trim() ||
    user.user_metadata.username ||
    user.email?.split('@')[0] ||
    `user_${user.id.slice(0, 8)}`;

  const { data, error } = await supabase
    .from('rental_profiles')
    .upsert(
      {
        id: user.id,
        username: nextUsername,
        email: user.email ?? null,
      },
      { onConflict: 'id' }
    )
    .select('*')
    .single();

  if (error) {
    throw new Error(normalizeAuthErrorMessage(error.message));
  }

  return data as RentalProfile;
}

export async function registerWithPassword(credentials: RegisterCredentials) {
  const { data, error } = await supabase.auth.signUp({
    email: credentials.email,
    password: credentials.password,
    options: {
      data: {
        username: credentials.username.trim(),
      },
    },
  });

  if (error) {
    throw new Error(normalizeAuthErrorMessage(error.message));
  }

  if (!data.user) {
    throw new Error('注册失败，请稍后再试。');
  }

  const profile = await upsertProfile(data.user, credentials.username);

  if (!data.session) {
    throw new Error(
      '注册已提交，但当前 Supabase 项目仍要求邮箱确认。测试环境请先关闭 Email confirmations。'
    );
  }

  return {
    session: data.session,
    user: data.user,
    profile,
  };
}

export async function loginWithPassword(credentials: AuthCredentials) {
  const { data, error } = await supabase.auth.signInWithPassword({
    email: credentials.email,
    password: credentials.password,
  });

  if (error) {
    throw new Error(normalizeAuthErrorMessage(error.message));
  }

  if (!data.user || !data.session) {
    throw new Error('登录失败，请稍后再试。');
  }

  const profile = await getRentalProfile(data.user.id);

  return {
    session: data.session,
    user: data.user,
    profile,
  };
}

export async function logout() {
  const { error } = await supabase.auth.signOut();
  if (error) {
    throw new Error(error.message);
  }
}

export async function getCurrentSession() {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession();

  if (error) {
    throw new Error(error.message);
  }

  return session;
}

export async function getRentalProfile(userId: string) {
  const { data, error } = await supabase
    .from('rental_profiles')
    .select('*')
    .eq('id', userId)
    .maybeSingle();

  if (error) {
    throw new Error(normalizeAuthErrorMessage(error.message));
  }

  return (data as RentalProfile | null) ?? null;
}

export function onAuthStateChange(
  callback: (event: AuthChangeEvent, session: Session | null) => void
) {
  return supabase.auth.onAuthStateChange(callback);
}
