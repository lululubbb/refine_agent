package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_8_2Test {

    private CSVRecord csvRecord;
    private String[] values;
    private Map<String, Integer> mapping;
    private String comment;
    private long recordNumber;

    @BeforeEach
    void setUp() throws Exception {
        values = new String[] { "value1", "value2", "value3" };
        mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        comment = "test comment";
        recordNumber = 123L;

        csvRecord = createCSVRecord(values, mapping, comment, recordNumber);
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Class<CSVRecord> clazz = CSVRecord.class;
        Constructor<CSVRecord> constructor = clazz.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    void testValuesMethod_returnsValuesArray() throws Exception {
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] result = (String[]) valuesMethod.invoke(csvRecord);
        assertArrayEquals(values, result);
    }

    @Test
    @Timeout(8000)
    void testValuesMethod_emptyValuesArray() throws Exception {
        CSVRecord emptyCsvRecord = createCSVRecord(new String[0], Collections.emptyMap(), null, 0L);
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] result = (String[]) valuesMethod.invoke(emptyCsvRecord);
        assertNotNull(result);
        assertEquals(0, result.length);
    }
}