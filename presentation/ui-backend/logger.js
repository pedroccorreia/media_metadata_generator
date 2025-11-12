const LOG_PREFIX = 'nebula-foundry-ui-backend';

const logger = {
  log: (...args) => {
    console.log(LOG_PREFIX, ...args);
  },
  error: (...args) => {
    console.error(LOG_PREFIX, ...args);
  },
  warn: (...args) => {
    console.warn(LOG_PREFIX, ...args);
  },
};

module.exports = logger;
