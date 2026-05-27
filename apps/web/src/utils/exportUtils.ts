// 导出工具函数

export interface ExportDocument {
  title: string;
  content: string;
  format?: 'markdown' | 'word' | 'pdf';
  type?: string;
  createdAt?: string;
  updatedAt?: string;
}

export function exportAsMarkdown(doc: ExportDocument | string, content?: string): string {
  if (typeof doc === 'string') {
    return `# ${doc}\n\n${content || ''}`;
  }
  return `# ${doc.title}\n\n${doc.content}`;
}

export function exportAsWord(doc: ExportDocument | string, content?: string): string {
  const title = typeof doc === 'string' ? doc : doc.title;
  const body = typeof doc === 'string' ? (content || '') : doc.content;

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>${title}</title>
  <style>
    body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; }
    h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
    h2 { color: #555; margin-top: 30px; }
    h3 { color: #666; }
    code { background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }
    pre { background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }
    blockquote { border-left: 4px solid #ddd; margin: 0; padding-left: 20px; color: #666; }
    table { border-collapse: collapse; width: 100%; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background: #f5f5f5; }
  </style>
</head>
<body>
  <h1>${title}</h1>
  ${body.replace(/\n/g, '<br/>')}
</body>
</html>`;
}

export function exportAsPDF(doc: ExportDocument | string, content?: string): void {
  const title = typeof doc === 'string' ? doc : doc.title;
  const body = typeof doc === 'string' ? (content || '') : doc.content;
  // 打开打印对话框，用户可以选择保存为 PDF
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
      <head>
        <title>${title}</title>
        <style>
          @media print {
            body { font-family: Arial, sans-serif; line-height: 1.6; }
            h1 { page-break-before: always; }
            h1:first-of-type { page-break-before: avoid; }
          }
          body { font-family: Arial, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 20px; }
          h1 { color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }
        </style>
      </head>
      <body>
        <h1>${title}</h1>
        ${(content || '').replace(/\n/g, '<br/>')}
        <script>window.print();</script>
      </body>
      </html>
    `);
    printWindow.document.close();
  }
}

export function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export interface PRDOptions {
  overview?: string;
  goals?: string[];
  features?: Array<{ name: string; description: string; priority: string }>;
  userStories?: Array<{ role: string; action: string; benefit: string }>;
  acceptanceCriteria?: string[];
  nonFunctionalRequirements?: string[];
  timeline?: string;
}

export function generatePRD(title: string, options?: PRDOptions): string {
  const overview = options?.overview || '[描述项目的背景和起因]';
  const goals = options?.goals?.map(g => `- ${g}`).join('\n') || '- [目标1]\n- [目标2]';
  const features = options?.features?.map(f =>
    `| ${f.priority} | ${f.name} | ${f.description} | [验收标准] |`
  ).join('\n') || '| P0 | [功能名称] | [功能描述] | [验收标准] |';

  return `# ${title}

## 1. 文档信息
- **版本**: 1.0
- **日期**: ${new Date().toLocaleDateString()}
- **作者**:
- **状态**: 草稿

## 2. 项目概述
### 2.1 背景
${overview}

### 2.2 目标
${goals}

### 2.3 范围
[描述项目的范围，包括包含和不包含的内容]

## 3. 功能需求
### 3.1 功能列表
| 优先级 | 功能名称 | 功能描述 | 验收标准 |
|--------|----------|----------|----------|
${features}

## 4. 非功能需求
### 4.1 性能要求
### 4.2 安全要求
### 4.3 兼容性要求

## 5. 里程碑
[描述项目的关键时间节点]

## 6. 附录
[其他补充信息]`;
}

export function generatePRDTemplate(title: string): string {
  return `# ${title}

## 1. 文档信息
- **版本**: 1.0
- **日期**: ${new Date().toLocaleDateString()}
- **作者**:
- **状态**: 草稿

## 2. 项目概述
### 2.1 背景
[描述项目的背景和起因]

### 2.2 目标
[描述项目的目标和预期成果]

### 2.3 范围
[描述项目的范围，包括包含和不包含的内容]

## 3. 用户画像
[描述目标用户群体]

## 4. 功能需求
### 4.1 功能列表
| 优先级 | 功能名称 | 功能描述 | 验收标准 |
|--------|----------|----------|----------|
| P0 | | | |
| P1 | | | |
| P2 | | | |

## 5. 用户故事
[描述具体的用户场景和故事]

## 6. 非功能需求
### 6.1 性能要求
### 6.2 安全要求
### 6.3 兼容性要求

## 7. 数据埋点
[描述需要追踪的数据指标]

## 8. 里程碑
[描述项目的关键时间节点]

## 9. 附录
[其他补充信息]`;
}

export interface MeetingMinutesOptions {
  title?: string;
  date?: string;
  attendees?: string[];
  agenda?: string[];
  discussions?: Array<{ topic: string; content: string }>;
  decisions?: string[];
  actionItems?: Array<{ task: string; assignee: string; dueDate: string }>;
}

export function generateMeetingMinutes(options?: MeetingMinutesOptions): string {
  const title = options?.title || '会议记录';
  const date = options?.date || new Date().toLocaleString();
  const attendees = options?.attendees?.map(a => `- ${a}`).join('\n') || '- [参会人员]';
  const agenda = options?.agenda?.map((a, i) => `${i + 1}. ${a}`).join('\n') || '1. [议程1]\n2. [议程2]';
  const discussions = options?.discussions?.map((d, i) => `### 议题${i + 1}: ${d.topic}\n${d.content}`).join('\n\n') || '### 议题1\n[讨论内容]';
  const decisions = options?.decisions?.map((d, i) => `${i + 1}. ${d}`).join('\n') || '1. [决议1]';
  const actionItems = options?.actionItems?.map((item, i) =>
    `| ${i + 1} | ${item.task} | ${item.assignee} | ${item.dueDate} | 待开始 |`
  ).join('\n') || '| 1 | [任务] | [负责人] | [截止日期] | 待开始 |';

  return `# ${title}

## 会议信息
- **时间**: ${date}
- **地点**:
- **参会人员**:
${attendees}
- **记录人**:

## 议程
${agenda}

## 讨论内容
${discussions}

## 决议
${decisions}

## 行动项
| 序号 | 任务 | 负责人 | 截止日期 | 状态 |
|------|------|--------|----------|------|
${actionItems}

## 下次会议
- **时间**:
- **主要议题**:

---
*会议记录自动生成*`;
}

export function exportAsFeishuDoc(content: string, title?: string): string {
  const header = `---\ndocument_type: feishu\nversion: 1.0\n---\n\n`;
  return header + (title ? `# ${title}\n\n` : '') + content;
}

export function exportAsFeishuCard(content: string, title?: string): string {
  const lines = content.split('\n');
  let cardTitle = title || '项目 PRD';
  for (const line of lines) {
    if (line.startsWith('# ')) {
      cardTitle = line.slice(2).trim();
      break;
    }
  }

  const sections: Array<{ heading: string; text: string }> = [];
  let currentH2 = '';
  let currentText: string[] = [];
  for (const line of lines) {
    if (line.startsWith('## ')) {
      if (currentH2 && currentText.length > 0) {
        sections.push({ heading: currentH2, text: currentText.slice(0, 10).join('\n') });
        currentText = [];
      }
      currentH2 = line.slice(3).trim();
    } else if (currentH2) {
      currentText.push(line.trim());
    }
  }
  if (currentH2 && currentText.length > 0) {
    sections.push({ heading: currentH2, text: currentText.slice(0, 10).join('\n') });
  }

  const elements: Array<Record<string, unknown>> = [
    { tag: 'markdown', content: `**${cardTitle}**\n生成时间：${new Date().toISOString().slice(0, 10)}` },
  ];
  for (const s of sections.slice(0, 5)) {
    elements.push({ tag: 'hr' });
    elements.push({ tag: 'markdown', content: `**${s.heading}**\n${s.text.slice(0, 200)}` });
  }

  return JSON.stringify({
    msg_type: 'interactive',
    card: {
      header: { title: { tag: 'plain_text', content: cardTitle } },
      elements,
    },
  }, null, 2);
}

export function exportAsWeChatWork(content: string): string {
  const result: string[] = [];
  for (const line of content.split('\n')) {
    if (line.startsWith('#')) {
      result.push(line);
    } else if (line.trim().startsWith('- ')) {
      result.push(`> ${line.trim().slice(2)}`);
    } else if (line.startsWith('|---') || line.startsWith('| ---')) {
      continue;
    } else if (line.startsWith('|')) {
      const cells = line.split('|').map(c => c.trim()).filter(Boolean);
      result.push(cells.join(' · '));
    } else {
      result.push(line);
    }
  }
  return result.join('\n');
}

export function generateGitHubIssue(title: string, content: string, labels: string[] = []): string {
  const baseUrl = 'https://github.com';
  const repo = 'owner/repo'; // 应该从配置中获取
  const issueTitle = encodeURIComponent(title);
  const issueBody = encodeURIComponent(content);
  const issueLabels = labels.map(l => `label=${encodeURIComponent(l)}`).join('&');

  return `${baseUrl}/${repo}/issues/new?title=${issueTitle}&body=${issueBody}${issueLabels ? '&' + issueLabels : ''}`;
}
