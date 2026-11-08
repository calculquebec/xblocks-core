import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";
import { page, server } from 'vitest/browser'

const renderButton = async () => {
    const block = document.createElement('div')
    block.setAttribute('id', 'xblock')
    block.innerHTML = `<ul>
                         <li class="pdf-download-button" data-testid="download-button">Download</li>
                       </ul>`
    document.body.appendChild(block)
}

/*
We need to load some scripts into the global browser context, since that's how they're loaded in an
XBlock environment. If we try to just import them, they'll be scoped to module contexts and won't be
able to affect global variables in the same way they would in production.
 */
const loadJsPayload = async (path: string, id?: string) => {
    const scriptTag = document.createElement('script')
    scriptTag.textContent = await server.commands.readFile(path)
    if (id) {
        scriptTag.setAttribute('id', id)
    }
    document.body.appendChild(scriptTag)
}

const JQueryDetails: Record<string, string> = {
    'src': 'https://code.jquery.com/jquery-3.7.1.js',
    'integrity': 'sha256-eKhayi8LEQwp4NKxN+CfCh+3qOVUtJn3QNZ0TciWLP4=',
    'crossorigin': 'anonymous'
} as const


// Can be used outside tests, whereas expect cannot.
const assert = ((value: unknown) => {
    if (!!value) {
        return
    }
    throw Error(`Assertion failed: ${value}`)
})


describe("PDF Block Initializer", () => {
    beforeEach(async () => {
        const scriptTag = document.createElement('script')
        Object.keys(JQueryDetails).forEach((key) => {
            scriptTag.setAttribute(key, JQueryDetails[key])
        })
        document.body.appendChild(scriptTag)
        await loadJsPayload('specs/helpers/proveJQuery.js')
        await vi.waitFor(() => assert(document.querySelector('div[data-testid="jquery-loaded"]')))
        await loadJsPayload('../static/js/pdf.js')
        await loadJsPayload('specs/helpers/mockRuntime.js')
    })
    afterEach(() => {
        // Vitest browser isolation isn't perfect, apparently but this makes it good enough.
        document.body.innerHTML = ''
    })
    const testButton = async () => {
        await vi.waitFor(async () => {
            const button = page.getByTestId('download-button')
            await button.click()
        })
        await vi.waitFor(() => expect.element(page.getByTestId('post-call')).toBeInTheDocument())
    }
    it("Sets a callback upon download when handed an element", async () => {
        await renderButton()
        await loadJsPayload('specs/helpers/loadAsElement.js', 'init')
        await testButton()
    })
    it("Sets a callback when handed a JQuery object", async () => {
        await renderButton()
        await loadJsPayload('specs/helpers/loadAsJQuery.js', 'init')
        await testButton()
    })
})
