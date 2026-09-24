import { Link } from "react-router";
import { BookOpen, KeyRound, MessageSquare, ShieldCheck, Wrench } from "lucide-react";
import { useI18n } from "@/i18n";

/** First-party help. Never silently navigate Tino users to an upstream account or billing site. */
export default function DocsPage() {
  const { locale } = useI18n();
  const chinese = locale.startsWith("zh");
  const items = chinese
    ? [
        { icon: MessageSquare, title: "开始对话", text: "打开对话页，创建新话题并选择模型。", href: "/chat" },
        { icon: KeyRound, title: "接入模型", text: "在模型与密钥设置中添加服务商 API 密钥或自定义兼容接口。模型密钥不是 Tino 登录密码。", href: "/models" },
        { icon: Wrench, title: "工具与技能", text: "在技能页管理已安装技能；终端、文件和浏览器能力受当前运行环境的权限控制。", href: "/skills" },
        { icon: ShieldCheck, title: "账号与数据", text: "公开服务需要先完成独立账号、会话、密钥和运行环境隔离，再开放注册。", href: "/system" },
      ]
    : [
        { icon: MessageSquare, title: "Start chatting", text: "Open Chat, start a new topic, and select a model.", href: "/chat" },
        { icon: KeyRound, title: "Connect models", text: "Add a provider key or compatible endpoint in model settings. A model key is not your Tino password.", href: "/models" },
        { icon: Wrench, title: "Tools and skills", text: "Manage installed skills; browser, files, and terminal depend on runtime permissions.", href: "/skills" },
        { icon: ShieldCheck, title: "Accounts and data", text: "Public registration requires isolated accounts, sessions, keys, and runtimes.", href: "/system" },
      ];

  return (
    <main className="mx-auto flex w-full max-w-4xl flex-col gap-8 px-5 py-8 sm:px-8">
      <div className="flex items-start gap-4">
        <div className="rounded-xl border border-midground/30 bg-midground/10 p-3 text-midground">
          <BookOpen className="size-6" aria-hidden="true" />
        </div>
        <div>
          <h1 className="text-2xl font-semibold text-display">Tino Agent</h1>
          <p className="mt-2 text-sm text-text-secondary">
            {chinese ? "你自己的 AI 工作区。以下帮助内容在 Tino Agent 内提供，不会跳转到第三方充值网站。" : "Your AI workspace. This help stays inside Tino Agent and never redirects to another service's billing site."}
          </p>
        </div>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        {items.map(({ icon: Icon, title, text, href }) => (
          <Link key={href} to={href} className="rounded-xl border border-current/15 bg-current/[0.025] p-5 transition-colors hover:border-midground/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-midground">
            <Icon className="mb-4 size-5 text-midground" aria-hidden="true" />
            <h2 className="font-semibold text-display">{title}</h2>
            <p className="mt-2 text-sm leading-6 text-text-secondary">{text}</p>
          </Link>
        ))}
      </div>
    </main>
  );
}
