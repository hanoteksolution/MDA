import type { ReactNode } from "react";
import { motion } from "framer-motion";
import { cn } from "@/utils/cn";
import { PageHeader } from "./PageHeader";
import { useSetPageMeta } from "@/contexts/PageMetaContext";
import { animation } from "@/design-system";

interface PageLayoutProps {
  title: string;
  description?: string;
  breadcrumbs?: string[];
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}

export function PageLayout({
  title,
  description,
  breadcrumbs,
  actions,
  children,
  className,
}: PageLayoutProps) {
  useSetPageMeta({ title, description, breadcrumbs });

  return (
    <motion.div
      variants={animation.stagger.container}
      initial="hidden"
      animate="show"
      className={cn("ds-page w-full", className)}
    >
      <motion.div variants={animation.stagger.item}>
        <PageHeader
          title={title}
          description={description}
          breadcrumbs={breadcrumbs}
          actions={actions}
        />
      </motion.div>
      <motion.div variants={animation.stagger.item} className="space-y-6">
        {children}
      </motion.div>
    </motion.div>
  );
}
