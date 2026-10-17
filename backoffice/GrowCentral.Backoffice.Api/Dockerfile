FROM mcr.microsoft.com/dotnet/sdk:8.0-alpine AS build
WORKDIR /src
COPY backoffice/GrowCentral.Backoffice.Domain/GrowCentral.Backoffice.Domain.csproj backoffice/GrowCentral.Backoffice.Domain/
COPY backoffice/GrowCentral.Backoffice.Api/GrowCentral.Backoffice.Api.csproj backoffice/GrowCentral.Backoffice.Api/
RUN dotnet restore backoffice/GrowCentral.Backoffice.Api/GrowCentral.Backoffice.Api.csproj
COPY backoffice/ backoffice/
RUN dotnet publish backoffice/GrowCentral.Backoffice.Api/GrowCentral.Backoffice.Api.csproj -c Release -o /out --no-restore

FROM mcr.microsoft.com/dotnet/aspnet:8.0-alpine AS runtime
WORKDIR /app
COPY --from=build /out .
ENV ASPNETCORE_URLS=http://0.0.0.0:8091
EXPOSE 8091
USER app
ENTRYPOINT ["dotnet", "GrowCentral.Backoffice.Api.dll"]
