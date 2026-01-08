import { motion } from 'framer-motion';
import { cn } from "@/lib/utils";

const NeumorphicCard = ({ children, className, delay = 0, onClick, variant = 'flat', ...props }) => {
  const variants = {
    flat: 'shadow-neu-flat dark:shadow-neu-flat-dark',
    pressed: 'shadow-neu-pressed dark:shadow-neu-pressed-dark',
    convex: 'shadow-neu-convex dark:shadow-neu-convex-dark',
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, y: 15 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay, ease: "easeOut" }}
      onClick={onClick}
      className={cn(
        "bg-neu-base dark:bg-neu-base-dark rounded-3xl p-6",
        variants[variant],
        className
      )}
      {...props}
    >
      {children}
    </motion.div>
  );
};

export default NeumorphicCard;
