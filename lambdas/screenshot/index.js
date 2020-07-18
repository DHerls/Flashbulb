const fs = require("fs");

const chromium = require("chrome-aws-lambda");

const AWS = require("aws-sdk");
const s3 = new AWS.S3();

exports.handler = async (event, context, callback) => {
    let result = null;
    let browser = null;
    
    const safeUrl = event.url.replace("://", "-").replace(/\//g, "__");
    const prefix = event.prefix || '';
    // const scriptsDir = '/tmp/scripts'
    // fs.mkdirSync(scriptsDir)
    try {
        browser = await chromium.puppeteer.launch({
            args: chromium.args,
            defaultViewport: chromium.defaultViewport,
            executablePath: await chromium.executablePath,
            headless: chromium.headless,
            ignoreHTTPSErrors: true,
        });
        
        let page = await browser.newPage();

        let scripts = [];

        page.on('response', async function(response) {
            if (response.url().match(/.+?\.js(?:\?.+)?/)){
                scripts.push(response.url())
            }
        })
        
        const localScreenshotPath = "/tmp/screenshot.png"
        const httpResponse = await page.goto(event.url || "https://example.com");
        await page.screenshot({ path: localScreenshotPath });
                
        const remoteScreenshotPath = prefix + safeUrl + ".png";
        
        const fileContent = fs.readFileSync(localScreenshotPath);
        const screenshotParams = {
            Bucket: event.bucket,
            Key: remoteScreenshotPath,
            Body: fileContent,
        };
        s3.upload(screenshotParams, function (err, data) {
            if (err) {
                throw err;
            }
            result = {"status": 200}
        });
        
        const pageInfo = {
            finalUrl: page.url(),
            title: await page.title(),
            content: await page.content(),
            headers: httpResponse.headers(),
            ipAddress: httpResponse.remoteAddress(),
            status: {
                code: httpResponse.status(),
                text: httpResponse.statusText()
            },
            scripts: scripts
        };
        
        let remotePageInfoPath = prefix + safeUrl + ".json";
        const pageInfoParams = {
            Bucket: event.bucket,
            Key: remotePageInfoPath,
            Body: JSON.stringify(pageInfo),
        };
        s3.upload(pageInfoParams, function (err, data) {
            if (err) {
                throw err;
            }
            result = { status: 200 };
        });
        
    } catch (error) {
        let errorPath = prefix + 'errors/' + safeUrl + '.txt'
        const errorParams = {
            Bucket: event.bucket,
            Key: errorPath,
            Body: error.stack,
        };
        s3.upload(errorParams, function (err, data) {
            if (err) {
                return callback(err);
            }
        });
        return callback(error);
    } finally {
        if (browser !== null) {
            await browser.close();
        }
    }
    
    return callback(null, result);
};