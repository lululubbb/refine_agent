package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import org.apache.commons.csv.CSVRecord;
import org.junit.jupiter.api.Test;
import java.lang.reflect.Method;
import java.util.Map;
import java.util.HashMap;

class CSVRecord_8_1Test {

    @Test
    @Timeout(8000)
    void testValues() throws Exception {
        String[] expectedValues = new String[]{"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        CSVRecord record = new CSVRecord(expectedValues, mapping, "comment", 1L);

        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] actualValues = (String[]) valuesMethod.invoke(record);

        assertArrayEquals(expectedValues, actualValues);
    }
}