package com.risklens.backend.client;

import static org.springframework.test.web.client.ExpectedCount.once;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.jsonPath;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.risklens.backend.domain.AnalystDecisionType;
import com.risklens.backend.dto.CaseMemoryRequest;
import com.risklens.backend.service.CaseMemoryEvent;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class CaseMemoryClientTest {

    @Test
    void postsCommittedAnalystDecisionToVerifierMemoryEndpoint() {
        RestClient.Builder builder = RestClient.builder().baseUrl("http://verifier.test");
        MockRestServiceServer server = MockRestServiceServer.bindTo(builder).build();
        CaseMemoryClient client = new CaseMemoryClient(builder.build());
        server.expect(once(), requestTo("http://verifier.test/api/v1/memory/cases"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(jsonPath("$.risk_case_id").value("CASE-TEST-001"))
                .andExpect(jsonPath("$.final_label").value("CONFIRMED_ABUSE"))
                .andExpect(jsonPath("$.feature_snapshot.ringRisk").value(0.91))
                .andExpect(jsonPath("$.evidence_snapshot[0].type").value("SHARED_DEVICE"))
                .andRespond(withSuccess("{}", MediaType.APPLICATION_JSON));

        client.index(new CaseMemoryEvent(new CaseMemoryRequest(
                "CASE-TEST-001",
                AnalystDecisionType.CONFIRMED_ABUSE,
                "Analyst confirmed a coordinated ring.",
                Map.of("ringRisk", 0.91),
                List.of(Map.of("type", "SHARED_DEVICE")))));

        server.verify();
    }
}
