"use client";

import { useState } from "react";
import { feedbackApi } from "@/lib/api";
import { toast } from "sonner";

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export default function FeedbackModal({ isOpen, onClose }: Props) {
  const [feedbackData, setFeedbackData] = useState({
    category: "feature" as "bug" | "feature" | "quality" | "other",
    content: "",
    rating: 0,
  });
  const [feedbackSubmitting, setFeedbackSubmitting] = useState(false);
  const [hoverRating, setHoverRating] = useState(0);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!feedbackData.content.trim()) return;
    setFeedbackSubmitting(true);
    try {
      await feedbackApi.submit({
        category: feedbackData.category,
        content: feedbackData.content,
        rating: feedbackData.rating > 0 ? feedbackData.rating : undefined,
        context: "dashboard",
      });
      onClose();
      setFeedbackData({ category: "feature", content: "", rating: 0 });
      toast.success("反馈已提交，感谢你的建议！");
    } catch {
      toast.error("提交失败，请重试");
    } finally {
      setFeedbackSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 px-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl p-6 w-full max-w-md">
        <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">
          💬 意见反馈
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              反馈类型
            </label>
            <select
              value={feedbackData.category}
              onChange={(e) =>
                setFeedbackData({ ...feedbackData, category: e.target.value as typeof feedbackData.category })
              }
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
            >
              <option value="feature">✨ 功能建议</option>
              <option value="bug">🐛 Bug 报告</option>
              <option value="quality">📝 生成质量</option>
              <option value="other">💡 其他</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              反馈内容
            </label>
            <textarea
              value={feedbackData.content}
              onChange={(e) =>
                setFeedbackData({ ...feedbackData, content: e.target.value })
              }
              className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-sky-500 dark:border-slate-600 dark:bg-slate-700 dark:text-white"
              placeholder="请描述你的建议或遇到的问题..."
              rows={4}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              评分（可选）
            </label>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((star) => (
                <button
                  key={star}
                  type="button"
                  onClick={() => setFeedbackData({ ...feedbackData, rating: star })}
                  onMouseEnter={() => setHoverRating(star)}
                  onMouseLeave={() => setHoverRating(0)}
                  className={`text-xl transition-colors cursor-pointer ${
                    (hoverRating || feedbackData.rating) >= star
                      ? "text-amber-400"
                      : "text-slate-300 dark:text-slate-600"
                  }`}
                >
                  ★
                </button>
              ))}
            </div>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-50 dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-700"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={feedbackSubmitting}
              className="flex-1 px-4 py-2 rounded-lg bg-sky-600 text-white hover:bg-sky-700 disabled:opacity-50"
            >
              {feedbackSubmitting ? "提交中..." : "提交"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
