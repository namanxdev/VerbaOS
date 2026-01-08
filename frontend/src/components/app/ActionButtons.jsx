import { motion } from 'framer-motion';

const ActionButtons = ({ intent, onAction }) => {
  // Mapping intent to possible follow-up actions
  const actionsMap = {
    water: ["Log Hydration", "Notify Nurse"],
    food: ["View Menu", "Request Snack"],
    medicine: ["Log Medication", "Call Pharmacy"],
    help: ["Call Nurse", "Emergency Contact"],
    emergency: ["CALL 911", "Alert All Staff", "False Alarm"],
    unknown: ["Retry", "Manual Entry"]
  };

  const currentActions = actionsMap[intent?.toLowerCase()] || actionsMap.unknown;

  if (!intent) return null;

  return (
    <div className="flex flex-wrap gap-4 justify-center mt-8">
      {currentActions.map((action, idx) => (
        <motion.button
          key={idx}
          onClick={() => onAction && onAction(action)}
          whileTap={{ scale: 0.97 }}
          aria-label={`Select action: ${action}`}
          className="bg-neu-base dark:bg-neu-base-dark text-slate-600 dark:text-slate-300 shadow-neu-btn dark:shadow-neu-btn-dark hover:shadow-neu-flat dark:hover:shadow-neu-flat-dark active:shadow-neu-pressed dark:active:shadow-neu-pressed-dark transition-all rounded-full px-8 py-4 text-sm font-medium"
        >
          {action}
        </motion.button>
      ))}
    </div>
  );
};

export default ActionButtons;