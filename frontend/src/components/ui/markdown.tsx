import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { cn } from "cn"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

const components: Components = {
  p: ({ className, ...props }) => (
    <p className={cn("leading-relaxed not-first:mt-3", className)} {...props} />
  ),
  a: ({ className, ...props }) => (
    <a
      className={cn("font-medium underline underline-offset-4", className)}
      target="_blank"
      rel="noreferrer"
      {...props}
    />
  ),
  ul: ({ className, ...props }) => (
    <ul className={cn("ms-5 list-disc not-first:mt-3", className)} {...props} />
  ),
  ol: ({ className, ...props }) => (
    <ol className={cn("ms-5 list-decimal not-first:mt-3", className)} {...props} />
  ),
  li: ({ className, ...props }) => <li className={cn("mt-1", className)} {...props} />,
  h1: ({ className, ...props }) => (
    <h1 className={cn("text-lg font-semibold not-first:mt-4", className)} {...props} />
  ),
  h2: ({ className, ...props }) => (
    <h2 className={cn("text-base font-semibold not-first:mt-4", className)} {...props} />
  ),
  h3: ({ className, ...props }) => (
    <h3 className={cn("text-sm font-semibold not-first:mt-3", className)} {...props} />
  ),
  blockquote: ({ className, ...props }) => (
    <blockquote
      className={cn(
        "border-l-2 border-border ps-3 text-muted-foreground not-first:mt-3",
        className
      )}
      {...props}
    />
  ),
  hr: ({ className, ...props }) => <hr className={cn("my-3 border-border", className)} {...props} />,
  code: ({ className, children, ...props }) => {
    const isBlock = className?.includes("language-")
    if (isBlock) {
      return (
        <code className={cn("font-mono text-xs", className)} {...props}>
          {children}
        </code>
      )
    }
    return (
      <code
        className={cn(
          "rounded bg-black/8 px-1 py-0.5 font-mono text-[0.85em] dark:bg-white/12",
          className
        )}
        {...props}
      >
        {children}
      </code>
    )
  },
  pre: ({ className, ...props }) => (
    <pre
      className={cn(
        "overflow-x-auto rounded-lg bg-black/8 p-3 not-first:mt-3 dark:bg-white/12",
        className
      )}
      {...props}
    />
  ),
  table: ({ className, ...props }) => (
    <div className="not-first:mt-3">
      <Table className={cn("border border-border", className)} {...props} />
    </div>
  ),
  thead: (props) => <TableHeader {...props} />,
  tbody: (props) => <TableBody {...props} />,
  tr: (props) => <TableRow {...props} />,
  th: (props) => <TableHead {...props} />,
  td: (props) => <TableCell {...props} />,
  strong: ({ className, ...props }) => <strong className={cn("font-semibold", className)} {...props} />,
}

function Markdown({ className, children }: { className?: string; children: string }) {
  return (
    <div className={cn("text-sm", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {children}
      </ReactMarkdown>
    </div>
  )
}

export { Markdown }
