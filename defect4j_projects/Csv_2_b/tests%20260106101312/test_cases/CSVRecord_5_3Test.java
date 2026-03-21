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

class CSVRecord_5_3Test {

    private CSVRecord csvRecordWithMapping;
    private CSVRecord csvRecordWithoutMapping;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() throws Exception {
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);

        String[] values = new String[] {"value1", "value2"};

        // Use reflection to get the package-private constructor
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        csvRecordWithMapping = constructor.newInstance((Object) values, mapping, "comment", 1L);
        csvRecordWithoutMapping = constructor.newInstance((Object) values, null, "comment", 1L);
    }

    @Test
    @Timeout(8000)
    void testIsMapped_withMappingContainsKey() {
        assertTrue(csvRecordWithMapping.isMapped("header1"));
        assertTrue(csvRecordWithMapping.isMapped("header2"));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_withMappingDoesNotContainKey() {
        assertFalse(csvRecordWithMapping.isMapped("header3"));
        assertFalse(csvRecordWithMapping.isMapped(null));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_withoutMapping() {
        assertFalse(csvRecordWithoutMapping.isMapped("header1"));
        assertFalse(csvRecordWithoutMapping.isMapped(null));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_reflectionInvocation() throws Exception {
        Method isMappedMethod = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        isMappedMethod.setAccessible(true);

        // invoke on csvRecordWithMapping with key present
        Object result1 = isMappedMethod.invoke(csvRecordWithMapping, "header1");
        assertTrue((Boolean) result1);

        // invoke on csvRecordWithMapping with key absent
        Object result2 = isMappedMethod.invoke(csvRecordWithMapping, "nonexistent");
        assertFalse((Boolean) result2);

        // invoke on csvRecordWithoutMapping
        Object result3 = isMappedMethod.invoke(csvRecordWithoutMapping, "header1");
        assertFalse((Boolean) result3);
    }
}