const LOG_PREFIX = 'nebula-foundry-ui';

export const logger = {
  log: (...args: any[]) => {
    console.log(LOG_PREFIX, ...args);
  },
  error: (...args: any[]) => {
    console.error(LOG_PREFIX, ...args);
  },
  warn: (...args: any[]) => {
    console.warn(LOG_PREFIX, ...args);
  },
};
