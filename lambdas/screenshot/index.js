const fs = require("fs");

const chromium = require("chrome-aws-lambda");

const AWS = require("aws-sdk");
const s3 = new AWS.S3();
const lambda = new AWS.Lambda();

const errorHandler = (error, prefix, safeUrl, event) => {
  let errorPath = prefix + "errors/" + safeUrl + ".txt";
  const errorParams = {
    Bucket: event.bucket,
    Key: errorPath,
    Body: error.stack,
  };
  s3.upload(errorParams, function (err, data) {
    if (err) {
      // Where is your god now?
    }
  });
};

exports.handler = async (event, context, callback) => {
  let result = null;
  let browser = null;

  const safeUrl = event.url.replace("://", "-").replace(/\//g, "__");
  const prefix = event.prefix || "";
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

    page.on("response", async function (response) {
      if (response.url().match(/.+?\.js(?:\?.+)?/)) {
        scripts.push(response.url());
      }
    });

    const localScreenshotPath = "/tmp/screenshot.png";
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
        errorHandler(err, prefix, safeUrl, event);
      }
      result = { status: 200 };
    });

    const meta = await page.$$eval("meta", (tags) => {
      let values = {};
      tags.forEach((tag) => {
        if (tag["name"]) {
          values[tag["name"]] = tag["content"];
        }
      });
      return values;
    });

    const pageInfo = {
      startUrl: event.url,
      bucket: event.bucket,
      prefix: event.prefix,
      finalUrl: page.url(),
      title: await page.title(),
      content: await page.content(),
      cookies: await page.cookies(),
      meta: meta,
      headers: httpResponse.headers(),
      ipAddress: httpResponse.remoteAddress(),
      status: {
        code: httpResponse.status(),
        text: httpResponse.statusText(),
      },
      scripts: scripts,
    };

    let remotePageInfoPath = prefix + safeUrl + ".json";
    const pageInfoParams = {
      Bucket: event.bucket,
      Key: remotePageInfoPath,
      Body: JSON.stringify(pageInfo),
    };

    const invokeParams = {
      FunctionName: "Flashbulb--Analyze",
      Payload: JSON.stringify(pageInfo),
      InvocationType: "Event",
    };

    if (Buffer.byteLength(invokeParams.Payload, "utf8") > 262144) {
      invokeParams.InvocationType = "RequestResponse";
    }

    lambda.invoke(invokeParams, (err, data) => {
      if (err) {
        errorHandler(err, prefix, safeUrl, event);
      }
    });
  } catch (error) {
    errorHandler(error, prefix, safeUrl, event);
    return callback(error);
  } finally {
    if (browser !== null) {
      await browser.close();
    }
  }

  return callback(null, result);
};
