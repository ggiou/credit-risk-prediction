FROM gradle:8.10-jdk17 AS builder

WORKDIR /workspace
COPY settings.gradle build.gradle ./
COPY spring-app/build.gradle spring-app/build.gradle
COPY spring-app/src spring-app/src
RUN gradle :spring-app:bootWar --no-daemon

FROM eclipse-temurin:17-jre

WORKDIR /app
COPY --from=builder /workspace/spring-app/build/libs/credit-risk-prediction.war app.war

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.war"]

