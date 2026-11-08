import type jQuery from 'jquery';
// We must use jQuery for handlers. Cannot use fetch or axios-- they won't have instrumentation applied to Studio's
// jQuery instance.
/* eslint-disable no-var */
declare var $: typeof jQuery;
