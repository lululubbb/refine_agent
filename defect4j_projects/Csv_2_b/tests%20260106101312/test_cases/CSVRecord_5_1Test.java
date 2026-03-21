package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_5_1Test {

    private CSVRecord recordWithMapping;
    private CSVRecord recordWithNullMapping;

    @BeforeEach
    void setUp() throws Exception {
        // Prepare a mapping map
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);

        // values array
        String[] values = new String[] { "value1", "value2" };

        // Use reflection to get the package-private constructor
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(
                String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);

        // record with mapping
        recordWithMapping = constructor.newInstance(values, mapping, "comment", 1L);

        // record with null mapping
        recordWithNullMapping = constructor.newInstance(values, null, "comment", 2L);
    }

    @Test
    @Timeout(8000)
    void testIsMapped_WithMappingContainsKeyTrue() {
        assertTrue(recordWithMapping.isMapped("header1"));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_WithMappingContainsKeyFalse() {
        assertFalse(recordWithMapping.isMapped("header3"));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_WithNullMapping() {
        assertFalse(recordWithNullMapping.isMapped("header1"));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_PrivateMethodReflection() throws Exception {
        // Using reflection to invoke isMapped (it's public)
        Method isMappedMethod = CSVRecord.class.getMethod("isMapped", String.class);
        isMappedMethod.setAccessible(true);

        // recordWithMapping and key present
        boolean result1 = (boolean) isMappedMethod.invoke(recordWithMapping, "header2");
        assertTrue(result1);

        // recordWithMapping and key absent
        boolean result2 = (boolean) isMappedMethod.invoke(recordWithMapping, "unknown");
        assertFalse(result2);

        // recordWithNullMapping
        boolean result3 = (boolean) isMappedMethod.invoke(recordWithNullMapping, "header1");
        assertFalse(result3);
    }
}