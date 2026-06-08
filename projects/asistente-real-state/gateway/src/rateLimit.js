/**
 * rateLimit.js — per-contact rate limiter using Redis.
 * Prevents flooding: max N messages per contact per time window.
 * Returns true if the message should be processed, false if rate-limited.
 */

const MAX_MESSAGES = parseInt(process.env.RL_MAX_MESSAGES || "10", 10);
const WINDOW_SECONDS = parseInt(process.env.RL_WINDOW_SECONDS || "60", 10);

let redis = null;

function setRedis(client) {
  redis = client;
}

/**
 * Check and increment rate limit for a contact.
 * @returns {boolean} true = allowed, false = rate-limited
 */
async function checkRateLimit(waContactId) {
  if (!redis) return true; // fail open if Redis unavailable

  const key = `rl:wa:${waContactId}`;
  try {
    const count = await redis.incr(key);
    if (count === 1) {
      await redis.expire(key, WINDOW_SECONDS);
    }
    if (count > MAX_MESSAGES) {
      console.warn(`[rate-limit] Contact ${waContactId} exceeded ${MAX_MESSAGES} msgs/${WINDOW_SECONDS}s`);
      return false;
    }
    return true;
  } catch (err) {
    console.error("[rate-limit] Redis error:", err.message);
    return true; // fail open
  }
}

/**
 * Check if a conversation is escalated to a human agent.
 * @returns {boolean} true = escalated (bot should stay silent)
 */
async function isEscalated(waContactId) {
  if (!redis) return false;
  try {
    const val = await redis.get(`escalate:${waContactId}`);
    return val !== null;
  } catch (_) {
    return false;
  }
}

module.exports = { setRedis, checkRateLimit, isEscalated };
