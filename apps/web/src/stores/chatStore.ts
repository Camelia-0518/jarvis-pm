import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface Message {
  id: string;
  conversationId: string;
  sender: {
    type: 'user' | 'agent' | 'system';
    id: string;
    name: string;
    role?: string;
  };
  content: string;
  type: 'text' | 'code' | 'image' | 'file';
  metadata?: {
    skillUsed?: string;
    referencedDocs?: string[];
    [key: string]: any;
  };
  parentId?: string;
  createdAt: string;
}

export interface Conversation {
  id: string;
  projectId: string;
  title?: string;
  status: 'active' | 'archived';
  messages: Message[];
  createdAt: string;
  updatedAt?: string;
}

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  isProcessing: boolean;

  // Actions
  setConversations: (conversations: Conversation[]) => void;
  createConversation: (projectId: string, title?: string) => Conversation;
  setCurrentConversation: (conversation: Conversation | null) => void;
  addMessage: (conversationId: string, message: Omit<Message, 'id' | 'createdAt'>) => void;
  updateConversation: (id: string, updates: Partial<Conversation>) => void;
  deleteConversation: (id: string) => void;
  getConversationByProject: (projectId: string) => Conversation[];
  setProcessing: (processing: boolean) => void;
}

const generateId = () => `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
const generateMessageId = () => `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversation: null,
      isProcessing: false,

      setConversations: (conversations) => set({ conversations }),

      createConversation: (projectId, title) => {
        const newConversation: Conversation = {
          id: generateId(),
          projectId,
          title: title || '新对话',
          status: 'active',
          messages: [],
          createdAt: new Date().toISOString(),
        };
        set((state) => ({
          conversations: [newConversation, ...state.conversations],
          currentConversation: newConversation,
        }));
        return newConversation;
      },

      setCurrentConversation: (conversation) => set({ currentConversation: conversation }),

      addMessage: (conversationId, messageData) => {
        const newMessage: Message = {
          ...messageData,
          id: generateMessageId(),
          createdAt: new Date().toISOString(),
        };

        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === conversationId
              ? {
                  ...conv,
                  messages: [...conv.messages, newMessage],
                  updatedAt: new Date().toISOString(),
                }
              : conv
          ),
          currentConversation:
            state.currentConversation?.id === conversationId
              ? {
                  ...state.currentConversation,
                  messages: [...state.currentConversation.messages, newMessage],
                  updatedAt: new Date().toISOString(),
                }
              : state.currentConversation,
        }));

        return newMessage;
      },

      updateConversation: (id, updates) =>
        set((state) => ({
          conversations: state.conversations.map((conv) =>
            conv.id === id ? { ...conv, ...updates, updatedAt: new Date().toISOString() } : conv
          ),
          currentConversation:
            state.currentConversation?.id === id
              ? { ...state.currentConversation, ...updates, updatedAt: new Date().toISOString() }
              : state.currentConversation,
        })),

      deleteConversation: (id) =>
        set((state) => ({
          conversations: state.conversations.filter((conv) => conv.id !== id),
          currentConversation: state.currentConversation?.id === id ? null : state.currentConversation,
        })),

      getConversationByProject: (projectId) => {
        return get().conversations.filter((conv) => conv.projectId === projectId);
      },

      setProcessing: (processing) => set({ isProcessing: processing }),
    }),
    {
      name: 'aipm-conversations',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversation: state.currentConversation,
      }),
    }
  )
);
