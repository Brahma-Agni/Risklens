FROM maven:3.9-eclipse-temurin-17-alpine AS build
WORKDIR /workspace

COPY pom.xml ./
COPY src ./src
RUN mvn --batch-mode clean package -DskipTests

FROM eclipse-temurin:17-jre-alpine
RUN addgroup -S risklens && adduser -S risklens -G risklens
WORKDIR /app

COPY --from=build /workspace/target/backend-*.jar app.jar

USER risklens
EXPOSE 8080
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "/app/app.jar"]
