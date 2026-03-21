package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_2_6Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() {
        values = new String[] { "value0", "value1", "value2" };
        mapping = new HashMap<>();
        mapping.put("col0", 0);
        mapping.put("col1", 1);
        mapping.put("col2", 2);
        csvRecord = new CSVRecord(values, mapping, "comment", 123L);
    }

    @Test
    @Timeout(8000)
    void testGetByIndex_ValidIndex() {
        for (int i = 0; i < values.length; i++) {
            assertEquals(values[i], csvRecord.get(i));
        }
    }

    @Test
    @Timeout(8000)
    void testGetByIndex_InvalidIndex_Negative() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(-1));
    }

    @Test
    @Timeout(8000)
    void testGetByIndex_InvalidIndex_TooLarge() {
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> csvRecord.get(values.length));
    }

    @Test
    @Timeout(8000)
    void testGetPrivateMethodUsingReflection() throws Exception {
        Method getMethod = CSVRecord.class.getDeclaredMethod("get", int.class);
        getMethod.setAccessible(true);
        for (int i = 0; i < values.length; i++) {
            String result = (String) getMethod.invoke(csvRecord, i);
            assertEquals(values[i], result);
        }
    }

    @Test
    @Timeout(8000)
    void testConstructorWithEmptyValues() {
        String[] emptyValues = new String[0];
        Map<String, Integer> emptyMapping = Collections.emptyMap();
        CSVRecord emptyRecord = new CSVRecord(emptyValues, emptyMapping, null, 0L);
        assertEquals(0, emptyRecord.size());
        assertThrows(ArrayIndexOutOfBoundsException.class, () -> emptyRecord.get(0));
    }
}