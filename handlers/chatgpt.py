from .base import BaseHandler

class ChatGPTHandler(BaseHandler):
    async def get_actions(self, page):
        # In a real app, you'd check if we are logged in here
        return {
            "site_type": "chat_interface",
            "available_actions": [
                {
                    "id": "send_message",
                    "type": "input",
                    "label": "Send Message to AI",
                    "param_name": "prompt"
                },
                {
                    "id": "get_last_response",
                    "type": "read",
                    "label": "Read latest reply"
                }
            ]
        }

    async def execute(self, page, action_id, params):
        if action_id == "send_message":
            prompt = params.get("prompt")
            
            # 1. Wait for and fill the textarea
            await page.wait_for_selector("#prompt-textarea", timeout=10000)
            await page.fill("#prompt-textarea", prompt)
            
            # 2. Click send
            await page.click("button[data-testid='send-button']")
            
            # 3. Wait for response to be generated
            try:
                # Wait for a message container to have actual content (the response)
                # Poll to see when new content appears after sending
                await page.wait_for_function("""() => {
                    // Get all message containers
                    const articles = document.querySelectorAll('[data-testid="conversation"] article');
                    if (articles.length === 0) return false;
                    
                    // Check the last article (should be AI response)
                    const lastArticle = articles[articles.length - 1];
                    const text = lastArticle.innerText || lastArticle.textContent || '';
                    
                    // Look for non-empty response that's not just "ChatGPT said:"
                    return text.length > 15 && !text.includes('ChatGPT said:');
                }""", timeout=60000)
                
            except Exception as e:
                print(f"Response generation timeout/error: {e}. Attempting to scrape anyway...")
                await page.wait_for_timeout(5000)
            
            return await self.scrape_latest(page)

        return {"error": "Invalid action"}

    async def scrape_latest(self, page):
        # Extract the last substantive message from the conversation
        last_msg = await page.evaluate("""() => {
            // Get all conversation articles
            const articles = document.querySelectorAll('[data-testid="conversation"] article');
            
            if (articles.length === 0) {
                // Fallback selectors
                const fallback = document.querySelectorAll('article');
                if (fallback.length > 0) {
                    return (fallback[fallback.length - 1].innerText || fallback[fallback.length - 1].textContent || 'No response yet').trim();
                }
                return 'No response yet';
            }
            
            // Get the last article (AI response)
            const lastArticle = articles[articles.length - 1];
            let text = lastArticle.innerText || lastArticle.textContent || '';
            
            // Clean up whitespace
            text = text.trim();
            
            // If we only got "ChatGPT said:" or similar, try to find the actual content
            if (text.length < 20) {
                // Look for nested markdown or content divs
                const content = lastArticle.querySelector('.markdown, [class*="content"], [class*="message"]');
                if (content) {
                    text = content.innerText || content.textContent || text;
                }
            }
            
            return text || 'No response yet';
        }""")
        return {"response": last_msg, "format": "markdown"}