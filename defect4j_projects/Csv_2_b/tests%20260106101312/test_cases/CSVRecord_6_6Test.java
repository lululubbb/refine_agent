package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_6_6Test {

    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    void setUp() {
        mapping = new HashMap<>();
        values = new String[]{"val0", "val1", "val2"};
    }

    @Test
    @Timeout(8000)
    void testIsSet_MappedAndIndexInRange() {
        mapping.put("key1", 1);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        assertTrue(csvRecord.isSet("key1"));
    }

    @Test
    @Timeout(8000)
    void testIsSet_MappedButIndexOutOfRange() {
        mapping.put("key1", 5);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        assertFalse(csvRecord.isSet("key1"));
    }

    @Test
    @Timeout(8000)
    void testIsSet_NotMapped() {
        mapping.put("key1", 1);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        assertFalse(csvRecord.isSet("unknown"));
    }

    @Test
    @Timeout(8000)
    void testIsSet_PrivateIsMappedMethodUsingReflection() throws Exception {
        mapping.put("key1", 0);
        csvRecord = new CSVRecord(values, mapping, null, 0L);

        Method isMappedMethod = CSVRecord.class.getDeclaredMethod("isMapped", String.class);
        isMappedMethod.setAccessible(true);

        boolean resultMapped = (boolean) isMappedMethod.invoke(csvRecord, "key1");
        boolean resultNotMapped = (boolean) isMappedMethod.invoke(csvRecord, "unknown");

        assertTrue(resultMapped);
        assertFalse(resultNotMapped);
    }
}