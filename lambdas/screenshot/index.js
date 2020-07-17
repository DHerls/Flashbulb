const fs = require("fs");

const chromium = require("chrome-aws-lambda");

const AWS = require("aws-sdk");
const s3 = new AWS.S3();

exports.handler = async (event, context, callback) => {
  let result = null;
  let browser = null;

  try {
    browser = await chromium.puppeteer.launch({
      args: chromium.args,
      defaultViewport: chromium.defaultViewport,
      executablePath: await chromium.executablePath,
      headless: chromium.headless,
      ignoreHTTPSErrors: true,
    });

    let page = await browser.newPage();
    
    const localScreenshotPath = "/tmp/screenshot.png"
    const httpResponse = await page.goto(event.url || "https://example.com");
    await page.screenshot({ path: localScreenshotPath });
    
    const safeUrl = event.url.replace("://", "-").replace(/\//g, "__");
    
    let remoteScreenshotPath = safeUrl + '.png';
    if (event.prefix){
        remoteScreenshotPath = event.prefix + '/' + remoteScreenshotPath;
    }

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
      ipAddress: httpResponse.remoteAddress(),
    };

    let remotePageInfoPath = safeUrl + ".json";
    if (event.prefix) {
      remotePageInfoPath = event.prefix + "/" + remotePageInfoPath;
    }
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
    return callback(error);
  } finally {
    if (browser !== null) {
      await browser.close();
    }
  }

  return callback(null, result);
};