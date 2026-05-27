import { create } from 'zustand';

interface User {
  id: string;
  name: string;
  avatar?: string;
  color: string;
  cursor?: { x: number; y: number };
  selection?: { start: number; end: number };
}

interface Comment {
  id: string;
  userId: string;
  userName: string;
  userAvatar: string;
  content: string;
  timestamp: Date;
  position?: { x: number; y: number };
  resolved: boolean;
}

interface CollaborationStore {
  // Connection
  isConnected: boolean;
  connectionError: string | null;

  // 在线用户
  onlineUsers: User[];
  currentUser: User | null;

  // 评论
  comments: Comment[];

  // 锁定段落
  lockedSections: Record<string, string>; // sectionId -> userId

  // Actions
  connect: (documentId: string, userName: string) => void;
  disconnect: () => void;
  setConnectionStatus: (connected: boolean, error?: string | null) => void;
  updateOnlineUsers: (users: User[]) => void;
  updateUserCursor: (userId: string, cursor: { x: number; y: number }) => void;
  removeUser: (userId: string) => void;
  addComment: (comment: Omit<Comment, 'id' | 'timestamp'>) => void;
  resolveComment: (commentId: string) => void;
  lockSection: (sectionId: string) => void;
  unlockSection: (sectionId: string) => void;
}

const COLORS = [
  '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
  '#8B5CF6', '#EC4899', '#06B6D4', '#F97316',
];

function pickColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return COLORS[Math.abs(hash) % COLORS.length];
}

export const useCollaborationStore = create<CollaborationStore>((set, get) => ({
  isConnected: false,
  connectionError: null,
  onlineUsers: [],
  currentUser: null,
  comments: [],
  lockedSections: {},

  connect: (documentId: string, userName: string) => {
    const userId = `user-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const color = pickColor(userName);
    const currentUser: User = {
      id: userId,
      name: userName,
      avatar: userName.slice(0, 2) || '👤',
      color,
    };

    set({
      currentUser,
      connectionError: null,
    });
  },

  disconnect: () => {
    set({
      isConnected: false,
      connectionError: null,
      onlineUsers: [],
      currentUser: null,
    });
  },

  setConnectionStatus: (connected, error = null) => {
    set({ isConnected: connected, connectionError: error });
  },

  updateOnlineUsers: (users) => {
    const { currentUser } = get();
    // Filter out current user from online users list
    const others = currentUser
      ? users.filter((u) => u.id !== currentUser.id)
      : users;
    set({ onlineUsers: others });
  },

  updateUserCursor: (userId, cursor) => {
    set((state) => ({
      onlineUsers: state.onlineUsers.map((u) =>
        u.id === userId ? { ...u, cursor } : u
      ),
    }));
  },

  removeUser: (userId) => {
    set((state) => ({
      onlineUsers: state.onlineUsers.filter((u) => u.id !== userId),
    }));
  },

  addComment: (comment) => {
    const newComment: Comment = {
      ...comment,
      id: `comment-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      timestamp: new Date(),
    };
    set((state) => ({
      comments: [...state.comments, newComment],
    }));
  },

  resolveComment: (commentId) => {
    set((state) => ({
      comments: state.comments.map((c) =>
        c.id === commentId ? { ...c, resolved: true } : c
      ),
    }));
  },

  lockSection: (sectionId) => {
    const { currentUser } = get();
    if (currentUser) {
      set((state) => ({
        lockedSections: { ...state.lockedSections, [sectionId]: currentUser.id },
      }));
    }
  },

  unlockSection: (sectionId) => {
    set((state) => {
      const newLocked = { ...state.lockedSections };
      delete newLocked[sectionId];
      return { lockedSections: newLocked };
    });
  },
}));
