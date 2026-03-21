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

class CSVRecord_5_6Test {

    private CSVRecord csvRecordWithMapping;
    private CSVRecord csvRecordWithoutMapping;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() throws Exception {
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);

        String[] values = new String[] { "value1", "value2" };

        // Use reflection to get the package-private constructor
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);

        csvRecordWithMapping = constructor.newInstance(values, mapping, "comment", 1L);
        csvRecordWithoutMapping = constructor.newInstance(values, null, "comment", 1L);
    }

    @Test
    @Timeout(8000)
    void testIsMapped_WithMapping_KeyExists() {
        assertTrue(csvRecordWithMapping.isMapped("header1"));
        assertTrue(csvRecordWithMapping.isMapped("header2"));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_WithMapping_KeyDoesNotExist() {
        assertFalse(csvRecordWithMapping.isMapped("nonexistent"));
        assertFalse(csvRecordWithMapping.isMapped(null));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_WithoutMapping() {
        assertFalse(csvRecordWithoutMapping.isMapped("header1"));
        assertFalse(csvRecordWithoutMapping.isMapped(null));
    }

    @Test
    @Timeout(8000)
    void testIsMapped_ReflectionInvocation() throws Exception {
        Method isMappedMethod = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        isMappedMethod.setAccessible(true);

        // With mapping and existing key
        Boolean result1 = (Boolean) isMappedMethod.invoke(csvRecordWithMapping, "header1");
        assertTrue(result1);

        // With mapping and non-existing key
        Boolean result2 = (Boolean) isMappedMethod.invoke(csvRecordWithMapping, "missing");
        assertFalse(result2);

        // Without mapping
        Boolean result3 = (Boolean) isMappedMethod.invoke(csvRecordWithoutMapping, "header1");
        assertFalse(result3);

        // Without mapping and null key
        Boolean result4 = (Boolean) isMappedMethod.invoke(csvRecordWithoutMapping, (Object) null);
        assertFalse(result4);
    }
}