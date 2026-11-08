import { defineConfig } from 'vitest/config'
import { playwright } from '@vitest/browser-playwright'

export default defineConfig({
    test: {
        isolate: true,
        browser: {
            enabled: true,
            provider: playwright(),
            instances: [{
                browser: 'firefox',
            }],
        },
    },
})
