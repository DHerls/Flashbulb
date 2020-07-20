const AWS = require("aws-sdk");
const s3 = new AWS.S3();

const fs = require("fs");
const Wappalyzer = require("wappalyzer-core");

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
// Wappalyzer wants objects in string => [string] format...
const processDict = (normalDict) => {
  let newDict = {};
  for (const [key, value] of Object.entries(normalDict)) {
    newDict[key] = [value];
  }
  return newDict;
};

const processCookies = (cookieList) => {
  const cookieDict = {};
  cookieList.forEach((cookie) => {
    cookieDict[cookie.name] = [cookie.value];
  });
  return cookieDict;
};

exports.handler = async (event, context, callback) => {
  const safeUrl = event.startUrl.replace("://", "-").replace(/\//g, "__");
  const prefix = event.prefix || "";

  try {
    const { apps: technologies, categories } = JSON.parse(
      fs.readFileSync("/opt/nodejs/node_modules/wappalyzer-core/apps.json")
    );

    Wappalyzer.setTechnologies(technologies);
    Wappalyzer.setCategories(categories);

    const detections = Wappalyzer.analyze({
      url: event.finalUrl,
      meta: processDict(event.meta),
      headers: processDict(event.headers),
      scripts: event.scripts,
      cookies: processCookies(event.cookies),
      html: event.content,
    });

    const results = Wappalyzer.resolve(detections);

    const pageInfo = {
      startUrl: event.startUrl,
      finalUrl: event.finalUrl,
      status: event.status,
      title: event.title,
      ipAddress: event.ipAddress,
      screenshot: prefix + safeUrl + '.png',
      technologies: results,
    };

    let remotePageInfoPath = prefix + safeUrl + ".json";
    const pageInfoParams = {
      Bucket: event.bucket,
      Key: remotePageInfoPath,
      Body: JSON.stringify(pageInfo),
    };
    await s3.upload(pageInfoParams, function (err, data) {
      if (err) {
        errorHandler(err, prefix, safeUrl, event);
      }
    });
    return callback(null, pageInfo);
  } catch (error) {
    errorHandler(err, prefix, safeUrl, event);
    return callback(error);
  }
};
