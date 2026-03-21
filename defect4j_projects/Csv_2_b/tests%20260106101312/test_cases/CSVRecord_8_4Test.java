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

class CSVRecord_8_4Test {

    private CSVRecord csvRecord;
    private String[] valuesArray;
    private Map<String, Integer> mapping;

    @BeforeEach
    void setUp() {
        valuesArray = new String[] {"value1", "value2", "value3"};
        mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        csvRecord = new CSVRecord(valuesArray, mapping, "comment", 123L);
    }

    @Test
    @Timeout(8000)
    void testValuesMethod_returnsCorrectArray() throws Exception {
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);

        String[] returnedValues = (String[]) valuesMethod.invoke(csvRecord);

        assertNotNull(returnedValues);
        assertArrayEquals(valuesArray, returnedValues);
        assertSame(valuesArray, returnedValues, "Returned array should be the exact same instance");
    }

    @Test
    @Timeout(8000)
    void testValuesMethod_withEmptyValues() throws Exception {
        CSVRecord emptyRecord = new CSVRecord(new String[0], Collections.emptyMap(), null, 0L);
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);

        String[] returnedValues = (String[]) valuesMethod.invoke(emptyRecord);

        assertNotNull(returnedValues);
        assertEquals(0, returnedValues.length);
    }

    @Test
    @Timeout(8000)
    void testValuesMethod_withNullCommentAndMapping() throws Exception {
        CSVRecord record = new CSVRecord(valuesArray, null, null, 0L);
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);

        String[] returnedValues = (String[]) valuesMethod.invoke(record);

        assertNotNull(returnedValues);
        assertArrayEquals(valuesArray, returnedValues);
    }
}